from openai import OpenAI
from django.shortcuts import get_object_or_404
from .models import  Consulta
from django.conf import settings

def transcribe_recording(id_consulta):
    consulta = get_object_or_404(Consulta, id=id_consulta)
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    with open(consulta.video.path, "rb") as f: 
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json", 
            language="pt",
        )

    consulta.transcricao = transcription.text
    consulta.save()
    return 'Ok'

def ocr_and_markdown_file(id_consulta):
    from docling.document_converter import DocumentConverter

    consulta = get_object_or_404(Consulta, id=id_consulta)

    converter = DocumentConverter()
    result = converter.convert(consulta.pdf.path)
    doc = result.document
    texto = doc.export_to_markdown()

    consulta.ocr_pdf = texto
    consulta.save()
    return 'Ok'

from .agent import SummaryAgent, ExamAnalysisAgent
def summary_and_exam_analysis(id_consulta):
    consulta = get_object_or_404(Consulta, id=id_consulta)
    summary_agent = SummaryAgent()
    resumo = summary_agent.run(consulta.transcricao)
    consulta.resumo = resumo.summaries
    exam_analysis_agent = ExamAnalysisAgent()
    analise_exames = exam_analysis_agent.run(consulta.ocr_pdf)
    consulta.analise_exames = analise_exames.analyses
    consulta.save()
    return 'Ok'