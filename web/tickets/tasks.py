import logging
import os
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
import requests
import ollama  # <--- IMPORTAMOS EL SDK OFICIAL
import ansible_runner
from .models import Ticket
_CHROMA_COLLECTION_ID = None
log = logging.getLogger(__name__)

# Configuración de entornos de contenedores
CHROMA_BASE  = os.getenv("CHROMA_URL", "http://chroma:8000")
OLLAMA_BASE  = os.getenv("OLLAMA_URL", "http://ollama:11434")
MODEL_NAME   = os.getenv("MODEL_NAME", "llama3:latest")
EMBED_MODEL  = os.getenv("EMBED_MODEL", "nomic-embed-text:latest")
COLL_NAME    = os.getenv("COLLECTION_NAME", "default")

# Lista blanca de playbooks permitidos para el validador y el esquema del LLM
PLAYBOOKS_PERMITIDOS = ['ping', 'reboot_service']

def inicializar_coleccion_chroma():
    global _CHROMA_COLLECTION_ID
    
    # Si el ID ya se obtuvo en una ejecución anterior en este worker, lo devolvemos directamente
    if _CHROMA_COLLECTION_ID is not None:
        return _CHROMA_COLLECTION_ID

    url_base = f"{CHROMA_BASE}/api/v1/collections"
    try:
        requests.post(url_base, json={"name": COLL_NAME, "metadata": {"description": "Historial de incidentes"}}, timeout=10)
        r = requests.get(url_base, timeout=10)
        r.raise_for_status()
        for c in r.json():
            if c["name"] == COLL_NAME:
                _CHROMA_COLLECTION_ID = c["id"]  # Guardamos en la caché global del módulo
                return _CHROMA_COLLECTION_ID
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
        raise RuntimeError("No se pudo establecer comunicación con ChromaDB.")

    try:
        # 1) Obtener Embeddings para Chroma
        emb_resp = requests.post(f"{OLLAMA_BASE}/api/embeddings", json={"model": EMBED_MODEL, "prompt": ticket.descripcion}, timeout=30)
        emb_resp.raise_for_status()
        embedding = emb_resp.json()["embedding"]

        # 2) Buscar incidentes similares en ChromaDB
        simil_resp = requests.post(f"{CHROMA_BASE}/api/v1/collections/{collection_id}/query", json={
            "query_embeddings": [embedding],
            "n_results": 3,
            "include": ["documents", "metadatas"]
        }, timeout=30)
        simil_resp.raise_for_status()
        
        data = simil_resp.json()
        lineas = []
        if data.get("ids") and len(data["ids"]) > 0:
            for i, doc_id in enumerate(data["ids"][0]):
                doc = data["documents"][0][i]
                meta = data["metadatas"][0][i] if data["metadatas"] else {}
                pb = meta.get("playbook", "unknown")
                lineas.append(f"- Incident: {doc} (playbook used: {pb})")
        contexto_previo = "\n".join(lineas)

        # 3) MEJORA 3: Inferencia estructurada con formato estricto JSON usando el SDK
# 3) Inferencia estructurada con formato estricto JSON usando el SDK
        prompt = f"""Eres un ingeniero DevOps. Analiza la incidencia, selecciona el playbook adecuado y extrae el host objetivo y el servicio afectado.
Incidencia actual: {ticket.descripcion}
Historial: {contexto_previo}
"""
        try:
            client = ollama.Client(host=OLLAMA_BASE)
            response = client.json(
                model=MODEL_NAME,
                prompt=prompt,
                schema={
                    'type': 'object',
                    'properties': {
                        'playbook': {
                            'type': 'string',
                            'enum': PLAYBOOKS_PERMITIDOS
                        },
                        'target_host': {
                            'type': 'string',
                            'description': 'El hostname o IP afectado. Usa localhost si no se puede deducir.'
                        },
                        'service_name': {
                            'type': 'string',
                            'description': 'El nombre del servicio afectado (ej. nginx, sshd). Deja vacío si no aplica.'
                        }
                    },
                    'required': ['playbook', 'target_host', 'service_name'],
                }
            )
            playbook_sugerido = response.get('playbook', 'ping')
            target_host = response.get('target_host', 'localhost')
            service_name = response.get('service_name', '')
        except Exception as e:
            log.error("Fallo en la inferencia estructurada del SDK: %s", e)
            playbook_sugerido = 'ping'
            target_host = 'localhost'
            service_name = ''

        playbook = playbook_sugerido if playbook_sugerido in PLAYBOOKS_PERMITIDOS else 'ping'

        # 4) Invocación de Ansible (Variables dinámicas)
        r = ansible_runner.run(
            private_data_dir='/srv/playbooks',
            playbook=f"project/{playbook}.yml",
            extravars={
                "ticket_id": ticket_id,
                "target_host": target_host,  # <-- Inyectado dinámicamente
                "service_name": service_name # <-- Inyectado dinámicamente
            },
            quiet=True
        )

        stdout_logs = r.stdout.read()[-2000:] if r.stdout else "No se obtuvo salida de Ansible."
        success = (r.rc == 0)

        # 5) Actualizar estado del ticket
        ticket.estado = "resolved" if success else "failed"
        ticket.playbook_usado = playbook
        ticket.solucion = stdout_logs
        ticket.save()

        _mail_admin(ticket, ok=success)

        if success:
            _upsert_to_chroma(ticket, collection_id, embedding, playbook)

        return {"ok": success, "playbook": playbook}

    except Exception as exc:
        log.exception("Error procesando el ticket %s: %s", ticket_id, exc)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        ticket.estado = "failed"
        ticket.solucion = f"Error tras agotar reintentos: {exc}"
        ticket.save()
        _mail_admin(ticket, ok=False)
        return {"ok": False, "error": str(exc)}

def _mail_admin(ticket: Ticket, ok: bool):
    subject = f"[Ticket #{ticket.id}] {'RESUELTO' if ok else 'FALLO'}"
    body = f"Resolución automatizada:\n\n{ticket.solucion}"
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL], fail_silently=True)

def _upsert_to_chroma(ticket, collection_id, embedding, playbook):
    payload = {
        "ids": [str(ticket.id)],
        "embeddings": [embedding],
        "documents": [ticket.descripcion],
        "metadatas": [{"playbook": playbook, "resolved": True}]
    }
    try:
        requests.post(f"{CHROMA_BASE}/api/v1/collections/{collection_id}/add", json=payload, timeout=20)
    except Exception as e:
        log.error("No se pudo indexar en ChromaDB: %s", e)