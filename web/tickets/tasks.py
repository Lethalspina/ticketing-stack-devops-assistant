from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from .models import Ticket
import requests
import ansible_runner
import logging
import os

log = logging.getLogger(__name__)

# Configuración leída directamente de las variables de entorno inyectadas al Worker
CHROMA_BASE  = os.getenv("CHROMA_URL", "http://chroma:8000")
OLLAMA_BASE  = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL_NAME   = os.getenv("MODEL_NAME", "llama3:latest")
EMBED_MODEL  = os.getenv("EMBED_MODEL", "nomic-embed-text:latest")
COLL_NAME    = os.getenv("COLLECTION_NAME", "default")

# LISTA BLANCA DE SEGURIDAD PARA EVITAR ALUCINACIONES DEL LLM
PLAYBOOKS_PERMITIDOS = ['ping', 'reboot_service']

def inicializar_coleccion_chroma():
    """Inicialización idempotente directa de la colección en ChromaDB."""
    url_base = f"{CHROMA_BASE}/api/v1/collections"
    try:
        # Intentar crearla por si no existe
        requests.post(url_base, json={"name": COLL_NAME, "metadata": {"description": "Historial de incidentes"}}, timeout=10)
        # Recuperar su ID único
        r = requests.get(url_base, timeout=10)
        r.raise_for_status()
        for c in r.json():
            if c["name"] == COLL_NAME:
                return c["id"]
    except Exception as e:
        log.error("Error conectando con ChromaDB al inicializar: %s", e)
    return None

@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def procesa_ticket(self, ticket_id: int):
    ticket = Ticket.objects.get(pk=ticket_id)
    ticket.estado = "running"
    ticket.save(update_fields=["estado"])

    collection_id = inicializar_coleccion_chroma()
    if not collection_id:
        raise RuntimeError("No se pudo establecer comunicación o ID válido con ChromaDB.")

    try:
        # 1) Obtener Embeddings directamente de Ollama
        emb_resp = requests.post(f"{OLLAMA_BASE}/api/embeddings", json={"model": EMBED_MODEL, "prompt": ticket.descripcion}, timeout=30)
        emb_resp.raise_for_status()
        embedding = emb_resp.json()["embedding"]

        # 2) Buscar incidentes similares en la colección de ChromaDB
        simil_resp = requests.post(f"{CHROMA_BASE}/api/v1/collections/{collection_id}/query", json={
            "query_embeddings": [embedding],
            "n_results": 3,
            "include": ["documents", "metadatas", "distances"]
        }, timeout=30)
        simil_resp.raise_for_status()
        
        data = simil_resp.json()
        lineas = []
        if data.get("ids") and len(data["ids"]) > 0:
            for i, doc_id in enumerate(data["ids"][0]):
                doc = data["documents"][0][i]
                meta = data["metadatas"][0][i] if data["metadatas"] else {}
                pb = meta.get("playbook", "unknown")
                resuelto = meta.get("resolved", False)
                lineas.append(f"- Incident: {doc} (playbook used: {pb}, resolved successfully: {resuelto})")
        contexto_previo = "\n".join(lineas)

        # 3) Formular prompt restringido a Ollama (Llama3)
        prompt = f"""Eres un ingeniero de soporte DevOps experto.
Descripción del incidente actual:
{ticket.descripcion}

Histórico de incidentes similares guardados en base de datos:
{contexto_previo}

De la siguiente lista de playbooks disponibles en el sistema:
- ping
- reboot_service

Debes emparejar el problema actual con uno de ellos. Si en incidentes pasados algo funcionó (resolved: True), priorízalo.
RESPONDE exactamente con una sola palabra de la lista (todo en minúsculas). No añadas explicaciones, ni introducciones, ni puntos.
"""

        comp_resp = requests.post(f"{OLLAMA_BASE}/api/generate", json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=120)
        comp_resp.raise_for_status()
        
        raw_response = comp_resp.json().get("response", "").strip().lower()
        playbook_sugerido = raw_response.splitlines()[0].strip() if raw_response else "ping"

        # --- VALIDACIÓN DE LISTA BLANCA (MÁXIMA ROBUSTEZ) ---
        if playbook_sugerido not in PLAYBOOKS_PERMITIDOS:
            log.warning("El LLM sugirió un playbook no autorizado '%s'. Aplicando fallback de seguridad.", playbook_sugerido)
            playbook = 'ping'
        else:
            playbook = playbook_sugerido

        log.info("Ticket %s procesado por IA -> Playbook seleccionado seguro: %s", ticket_id, playbook)

        # 4) Ejecutar Ansible de forma nativa mediante Ansible Runner
        r = ansible_runner.run(
            private_data_dir='/srv/playbooks',
            playbook=f"project/{playbook}.yml",
            extravars={"ticket_id": ticket_id},
            quiet=True
        )

        stdout_logs = r.stdout.read()[-2000:] if r.stdout else "No se obtuvo salida del proceso de automatización."
        success = (r.rc == 0)

        # 5) Persistencia de los resultados del diagnóstico en la base de datos relacional
        ticket.estado = "resolved" if success else "failed"
        ticket.playbook_usado = playbook
        ticket.solucion = stdout_logs
        ticket.save()

        # Notificar por Email al Administrador de Sistemas
        _mail_admin(ticket, ok=success)

        # 6) Si la ejecución fue exitosa, realimentar la memoria semántica en ChromaDB (RAG Continua)
        if success:
            _upsert_to_chroma(ticket, collection_id, embedding, playbook)

        return {"ok": success, "playbook": playbook}

    except Exception as exc:
        log.exception("Error crítico procesando el ticket %s: %s", ticket_id, exc)
        # CORREGIDO: Modificado para asegurar que el reintento funcione de forma limpia.
        # Solo marcamos el ticket como fallido de forma definitiva cuando se agoten los reintentos.
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        else:
            ticket.estado = "failed"
            ticket.solucion = f"Procesamiento abortado tras agotar reintentos del sistema. Excepción: {exc}"
            ticket.save()
            _mail_admin(ticket, ok=False)
        return {"ok": False, "error": str(exc)}

def _mail_admin(ticket: Ticket, ok: bool):
    subject = f"[Ticket #{ticket.id}] {'RESUELTO POR IA' if ok else 'FALLO EN AUTOMATIZACIÓN'}"
    body = f"Resultado de la remediación automatizada:\n\n{ticket.solucion}"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL], fail_silently=True)

def _upsert_to_chroma(ticket, collection_id, embedding, playbook):
    payload = {
        "ids": [str(ticket.id)],
        "embeddings": [embedding],
        "documents": [ticket.descripcion],
        "metadatas": [{"playbook": playbook, "resolved": True}]
    }
    try:
        resp = requests.post(f"{CHROMA_BASE}/api/v1/collections/{collection_id}/add", json=payload, timeout=20)
        resp.raise_for_status()
        log.info("Memoria RAG actualizada en ChromaDB para el Ticket %s", ticket.id)
    except Exception as e:
        log.error("No se pudo indexar el Ticket %s en la memoria semántica: %s", ticket.id, e)