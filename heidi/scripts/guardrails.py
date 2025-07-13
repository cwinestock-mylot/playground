from pydantic import BaseModel
import variables
import os
from openai import OpenAI


CLIENT = OpenAI(api_key=variables.OpenAI.api_key)


def validate_doc_note(doc_note):
    class DocNoteOutput(BaseModel):
        is_doc_note: bool
        reasoning: str

    prompt_path = os.path.join(variables.PROMPTS_DIR, "doc_note_validation_prompt.txt")
    prompt = open(prompt_path).read()
    prompt = prompt.replace('{{doc_note}}', doc_note)

    print("Validating doctor's note..")
    response = CLIENT.responses.parse(
        model="gpt-4o-mini",
        input=[
            {
                "role": "user",
                "content": prompt
            },
        ],
        text_format=DocNoteOutput,
    )
    print('Validation complete.')
    eval_result = {"is_doc_note": response.output_parsed.is_doc_note,
                   "is_doc_note_reasoning": response.output_parsed.reasoning}
    return eval_result
