from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from models.model_type import ModelType
from models.medical_condition import MedicalResponse
from dotenv import load_dotenv
import os
import re


load_dotenv()

# Non-empty placeholders so the app can boot without OPEN_AI_CHAT / CLAUDE_3_OPUS set.
# Real inference will fail until valid keys are configured.
_DEV_PLACEHOLDER_KEY = "sk-not-configured"


class MultiModel:

    def __init__(self) -> None:
        openai_key = os.environ.get("OPEN_AI_CHAT") or _DEV_PLACEHOLDER_KEY
        claude_key = os.environ.get("CLAUDE_3_OPUS") or _DEV_PLACEHOLDER_KEY

        self.openai_gpt_40 = ChatOpenAI(
            model_name="gpt-4o",
            openai_api_key=openai_key,
        )

        self.claude_opus = ChatAnthropic(
            model="claude-3-opus-20240229",
            api_key=claude_key,
            temperature=0,
            max_tokens=4000,
        )


        self.primary_parser = JsonOutputParser(pydantic_object=MedicalResponse)

        self.diagnosis_prompt=PromptTemplate(
            template="""
                You are a medical diagnosis assistant, skilled in recognizing diseases and prescribing treatments.
                
                if a patient has the condition, give me a list of diagnosis\n\n
                Condition: {condition}

                OUTPUT FORMAT INSTRUCTIONS:
                {format_instructions}
            """,
            input_variables=["condition"],
            partial_variables={"format_instructions": self.primary_parser.get_format_instructions()}
        )

        self._gpt_chain = None
        self._claude_chain = None

    def __clean_json_response(self, response: str) -> str:
        match = re.search(r'({.*}|\[.*\])', response, re.DOTALL)
        if match:
            return match.group(0) 
        raise ValueError("No valid JSON found in response")
    
    def __process_claude_output(self, ai_message):
        response_text = ai_message.content
        
        cleaned_response = self.__clean_json_response(response_text)
        
        return cleaned_response

    def _gpt_model(self):
        if self._gpt_chain is None:
            self._gpt_chain = self.diagnosis_prompt | self.openai_gpt_40 | self.primary_parser
        return self._gpt_chain

    def _claude_opus(self):
        if self._claude_chain is None:
            self._claude_chain = (
                self.diagnosis_prompt
                | self.claude_opus
                | (lambda x: self.__process_claude_output(x))
                | self.primary_parser
            )
        return self._claude_chain

    def invoke_model(self, model_type: ModelType, condition: str):
        if model_type == ModelType.GPT_4:
            chain = self._gpt_model()

        elif model_type == ModelType.CLAUDE:
            chain = self._claude_opus()

        else:
            raise ValueError("Invalid model type specified.")
        
        try:
            result = chain.invoke(condition)
            return result
        
        except OutputParserException as e:
            print(f"Error parsing output: {e}")
            raise e
        