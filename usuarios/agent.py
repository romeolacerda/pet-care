from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from django.conf import settings
from abc import abstractmethod
from langchain_core.prompts import ChatPromptTemplate
from prompts.prompt import SUMMARY_PROMPT, EXAM_ANALYSIS_PROMPT
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from pathlib import Path
from agno.skills import LocalSkills, Skills
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb
from agno.db.sqlite import SqliteDb
import httpx
from agno.tools import tool


load_dotenv()
SKILLS_DIR = Path(__file__).parent / "skills"

class TriagemResponse(BaseModel):
    cor: str = Field(description="A cor da triagem: verde, amarelo, laranja, vermelho")

class TriagemAgent:

    @classmethod
    def build_agent(cls):
        return Agent(
            name="TriagemAgent",
            model=OpenAIResponses(id="gpt-5-mini"),
            description=(
                "Realiza a triagem de um paciente com base nos dados de entrada; "
                "use a skill triagem para realizar a triagem."
            ),
            instructions=["Use a skill triagem-veterinaria para realizar a triagem."],
            output_schema=TriagemResponse,
            skills=Skills(loaders=[LocalSkills(str(SKILLS_DIR))]),
        )

    @classmethod
    def mount_prompt(self, frequencia_cardiaca, frequencia_respiratoria, temperatura, peso, queixa, observacao):
        return f"""
            Frequencia Cardiaca: {frequencia_cardiaca} bpm
            Frequencia Respiratoria: {frequencia_respiratoria} mpm
            Temperatura: {temperatura} °C
            Peso: {peso} kg
            Queixa: {queixa}
            Observacao: {observacao}
        """


@tool("buscar_eventos_adversos_veterinarios")
def buscar_eventos_adversos_veterinarios(
    medicamento: str,
    tipo_busca: str = "principio_ativo",
    especie: str = "",
    limite: int = 5,
) -> str:
    """Busca eventos adversos veterinários reportados ao FDA para um medicamento.
 
    Args:
        medicamento: Nome comercial ou princípio ativo. Ex: "Meloxicam", "Rimadyl", "Amoxicillin".
        tipo_busca: "principio_ativo" ou "nome_comercial". Padrão: "principio_ativo".
        especie: Filtrar por espécie. Ex: "Dog", "Cat", "Horse". Vazio para todas.
        limite: Quantidade de casos (1-10). Padrão: 5.
 
    Returns:
        JSON com estatísticas agregadas (reações, desfechos, espécies) e casos individuais do FDA.
    """
    BASE_URL = "https://api.fda.gov/animalandveterinary/event.json"
    limite = max(1, min(limite, 10))
    campo = "drug.brand_name" if tipo_busca == "nome_comercial" else "drug.active_ingredients.name"
 
    query = f'{campo}:"{medicamento}"'
    if especie:
        query += f'+AND+animal.species:"{especie}"'
 
    resp = httpx.get(BASE_URL, params={"search": query, "limit": str(limite)}, timeout=15)
    return resp.text
class AssistantAgent:
    VECTOR_DB_TABLE = "documentos"
    VECTOR_DB_URI = "lancedb"
    MEMORY_DB_FILE = "db.sqlite3"
    MEMORY_TABLE = "my_memory_table"
    AGENT_NAME = "Assistente Veterinario Virtual"
    AGENT_DESCRIPTION = (
        "Assistente virtual especializado em consultas veterinarias "
        "use a base de conhecimento de consultas veterinarias"
    )
    INSTRUCTIONS = """
    SUAS CAPACIDADES:
    1. Acesso a Base de Conhecimento (RAG): Você possui acesso a uma base de dados 
       e deve usá-la para responder as perguntas do usuário de forma precisa e fundamentada.
    2. Consulta de Medicamentos: Você pode buscar informações sobre medicamentos 
       através da API do FDA.
    
    DIRETRIZES:
    - Sempre priorize informações da base de conhecimento quando disponíveis.
    - Ao consultar medicamentos, forneça informações claras e organizadas.
    - Se não tiver certeza sobre alguma informação, indique isso ao usuário.
    - Mantenha um tom profissional e objetivo em todas as respostas.
    - Sempre devolva a resposta em markdown
    - Sempre que solicitado informacoes sobre medicamentos ou principios ativos, use a tools buscar_eventos_adversos_veterinarios para consultar no FDA.
    - Quando buscar informacoes sobre medicamentos ou principios ativos, nunca devolva a resposta da API traga a sua interpretacao dos dados com o contexto da pergunta.
    """

    knowledge = Knowledge(
        vector_db=LanceDb(
            table_name=VECTOR_DB_TABLE,
            uri=VECTOR_DB_URI,
            embedder=OpenAIEmbedder()
        ),
    )

    @classmethod
    def build_agent(cls, knowledge_filters: dict = {}, session_id: int = 0) -> Agent:
        db = SqliteDb(
            db_file=cls.MEMORY_DB_FILE,
            memory_table=cls.MEMORY_TABLE
        )
        
        return Agent(
            model=OpenAIResponses(id="gpt-5-mini"),
            name=cls.AGENT_NAME,
            description=cls.AGENT_DESCRIPTION,
            instructions=cls.INSTRUCTIONS,
            db=db,
            tools=[buscar_eventos_adversos_veterinarios,],
            update_memory_on_run=True,
            knowledge=cls.knowledge,
            knowledge_filters=knowledge_filters,
            search_knowledge=True,
            session_id=session_id,
        )
        
class Summaries(BaseModel):
    summaries: str = Field(description='Resumo')

class ExamAnalyses(BaseModel):
    analyses: list[str] = Field(description='Lista de análises')

class BaseAgent:
    llm = ChatOpenAI(model_name='gpt-5-mini', openai_api_key=settings.OPENAI_API_KEY)
    language: str = 'pt-br'
    audience: str = 'Veterinario'

    @abstractmethod
    def _prompt(self): ...

    @abstractmethod
    def run(self): ...

class SummaryAgent(BaseAgent):
    def _prompt(self):
        prompt = ChatPromptTemplate.from_messages([
            ('system', SUMMARY_PROMPT),
            ('human', 'language: {language} | audience: {audience}\nUse a transcrição abaixo: {transcription}')])

        return prompt
    
    def run(self, transcription):
        chain = self._prompt() | self.llm.with_structured_output(Summaries)
        return chain.invoke({'transcription': transcription, 'language': self.language, 'audience': self.audience})

class ExamAnalysisAgent(BaseAgent):

    def _prompt(self):
        prompt = ChatPromptTemplate.from_messages([
            ('system', EXAM_ANALYSIS_PROMPT),
            ('human', 'language: {language} | audience: {audience}\nExames: {exam_results}')])

        return prompt
    
    def run(self, exam_results):
        chain = self._prompt() | self.llm.with_structured_output(ExamAnalyses)
        return chain.invoke({'exam_results': exam_results, 'language': self.language, 'audience': self.audience})
        