from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Consulta
from .tasks import (
    ocr_and_markdown_file,
    transcribe_recording,
    summary_and_exam_analysis,
    rag_documentos,
)
from django_q.tasks import Chain


@receiver(post_save, sender=Consulta)
def signals_gravacoes_transcricao_resumos(sender, instance, created, **kwargs):
    if created:
        chain = Chain()
        chain.append(transcribe_recording, instance.id)
        chain.append(ocr_and_markdown_file, instance.id)
        chain.append(summary_and_exam_analysis, instance.id)
        chain.append(rag_documentos, instance.id)
        chain.run()
