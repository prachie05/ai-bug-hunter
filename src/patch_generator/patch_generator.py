from openai import OpenAI

from src.investigator.state import InvestigatorState
from src.patch_generator.prompts import PATCH_GENERATOR_PROMPT
from src.config import INVESTIGATOR_MODEL
from src.patch_generator.schemas import GeneratedPatch

client = OpenAI()

def patch_generator(state:InvestigatorState):
    prompt = PATCH_GENERATOR_PROMPT.format(
        bug_description = state.bug_description,
        hypothesis =state.hypothesis,
        generated_test = state.generated_test,
        retrieved_chunks = state.retrieved_chunks
    )

    response = client.responses.parse(
        model=INVESTIGATOR_MODEL,
        input= prompt,
        text_format= GeneratedPatch
    )

    return {
        "generated_patch" : response.output_parsed
    }