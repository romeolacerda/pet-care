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
        