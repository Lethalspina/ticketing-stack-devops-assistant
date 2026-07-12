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
PLAYBOOKS_PERMITIDOS = ['ping', 'reboot_service'][cite: 1]

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
    ticket = Ticket.objects.get(pk=ticket_id)[cite: 1]
    ticket.estado = "running"
    ticket.save(update_fields=["estado"])[cite: 1]

    collection_id = inicializar_coleccion_chroma()
    if not collection_id:
        raise RuntimeError("No se pudo establecer comunicación o ID válido con ChromaDB.")

    try:
        # 1) Obtener Embeddings directamente de Ollama
        emb_resp = requests.post(f"{OLLAMA_BASE}/api/embeddings", json={"model": EMBED_MODEL, "prompt": ticket.descripcion}, timeout=30)[cite: 1]
        emb_resp.raise_for_status()
        embedding = emb_resp.json()["embedding"][cite: 1]

        # 2) Buscar incidentes similares en la colección de ChromaDB
        simil_resp = requests.post(f"{CHROMA_BASE}/api/v1/collections/{collection_id}/query", json={
            "query_embeddings": [embedding],
            "n_results": 3,
            "include": ["documents", "metadatas", "distances"]
        }, timeout=30)[cite: 1]
        simil_resp.raise_for_status()
        
        data = simil_resp.json()
        lineas = []
        if data.get("ids") and len(data["ids"]) > 0:
            for i, doc_id in enumerate(data["ids"][0]):
                doc = data["documents"][0][i][cite: 1]
                meta = data["metadatas"][0][i] if data["metadatas"] else {}[cite: 1]
                pb = meta.get("playbook", "unknown")[cite: 1]
                resuelto = meta.get("resolved", False)[cite: 1]
                lineas.append(f"- Incident: {doc} (playbook used: {pb}, resolved successfully: {resuelto})")[cite: 1]
        contexto_previo = "\n".join(lineas)[cite: 1]

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
"""[cite: 1]

        comp_resp = requests.post(f"{OLLAMA_BASE}/api/generate", json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=120)[cite: 1]
        comp_resp.raise_for_status()
        
        raw_response = comp_resp.json().get("response", "").strip().lower()
        playbook_sugerido = raw_response.splitlines()[0].strip() if raw_response else "ping"[cite: 1]

        # --- VALIDACIÓN DE LISTA BLANCA (MÁXIMA ROBUSTEZ) ---
        if playbook_sugerido not in PLAYBOOKS_PERMITIDOS:
            log.warning("El LLM sugirió un playbook no autorizado '%s'. Aplicando fallback de seguridad.", playbook_sugerido)
            playbook = 'ping' # Fallback de seguridad por defecto
        else:
            playbook = playbook_sugerido

        log.info("Ticket %s procesado por IA -> Playbook seleccionado seguro: %s", ticket_id, playbook)[cite: 1]

        # 4) Ejecutar Ansible de forma nativa mediante Ansible Runner
        r = ansible_runner.run(
            private_data_dir='/srv/playbooks',
            playbook=f"project/{playbook}.yml",[cite: 1]
            extravars={"ticket_id": ticket_id},[cite: 1]
            quiet=True[cite: 1]
        )

        stdout_logs = r.stdout.read()[-2000:] if r.stdout else "No se obtuvo salida del proceso de automatización."[cite: 1]
        success = (r.rc == 0)[cite: 1]

        # 5) Persistencia de los resultados del diagnóstico en la base de datos relacional
        ticket.estado = "resolved" if success else "failed"[cite: 1]
        ticket.playbook_usado = playbook[cite: 1]
        ticket.solucion = stdout_logs[cite: 1]
        ticket.save()[cite: 1]

        # Notificar por Email al Administrador de Sistemas
        _mail_admin(ticket, ok=success)[cite: 1]

        # 6) Si la ejecución fue exitosa, realimentar la memoria semántica en ChromaDB (RAG Continua)
        if success:
            _upsert_to_chroma(ticket, collection_id, embedding, playbook)[cite: 1]

        return {"ok": success, "playbook": playbook}[cite: 1]

    except Exception as exc:
        log.exception("Error crítico procesando el ticket %s: %s", ticket_id, exc)[cite: 1]
        try:
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc)[cite: 1]
        finally:
            ticket.estado = "failed"[cite: 1]
            ticket.solucion = f"Procesamiento abortado por excepción del sistema: {exc}"[cite: 1]
            ticket.save()[cite: 1]
            _mail_admin(ticket, ok=False)[cite: 1]
        return {"ok": False, "error": str(exc)}[cite: 1]

def _mail_admin(ticket: Ticket, ok: bool):
    subject = f"[Ticket #{ticket.id}] {'RESUELTO POR IA' if ok else 'FALLO EN AUTOMATIZACIÓN'}"[cite: 1]
    body = f"Resultado de la remediación automatizada:\n\n{ticket.solucion}"[cite: 1]
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL], fail_silently=True)[cite: 1]

def _upsert_to_chroma(ticket, collection_id, embedding, playbook):
    payload = {
        "ids": [str(ticket.id)],[cite: 1]
        "embeddings": [embedding],[cite: 1]
        "documents": [ticket.descripcion],[cite: 1]
        "metadatas": [{"playbook": playbook, "resolved": True}][cite: 1]
    }
    try:
        resp = requests.post(f"{CHROMA_BASE}/api/v1/collections/{collection_id}/add", json=payload, timeout=20)[cite: 1]
        resp.raise_for_status()
        log.info("Memoria RAG actualizada en ChromaDB para el Ticket %s", ticket.id)[cite: 1]
    except Exception as e:
        log.error("No se pudo indexar el Ticket %s en la memoria semántica: %s", ticket.id, e)[cite: 1]