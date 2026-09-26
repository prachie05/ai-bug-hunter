from openai import OpenAI

from src.config import INVESTIGATOR_MODEL
from src.investigator.state import InvestigatorState
from src.test_generator.prompts import TEST_GENERATOR_PROMPT
from src.test_generator.schemas import GeneratedTest

client = OpenAI()

def generator_test(state: InvestigatorState):
    prompt = TEST_GENERATOR_PROMPT.format(
        bug_description = state.bug_description,
        hypothesis= state.hypothesis,
        retrieved_chunks= state.retrieved_chunks
        )

    response = client.responses.parse(
        model = INVESTIGATOR_MODEL,
        input= prompt,
        text_format =GeneratedTest
    )

    return {
        "generated_test": response.output_parsed
    }
