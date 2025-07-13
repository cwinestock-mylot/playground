import os
import variables
import json
import re
from bs4 import BeautifulSoup, NavigableString
from openai import OpenAI
from pydantic import BaseModel
from vector_store import fetch_vector_store

CLIENT = OpenAI(api_key=variables.OpenAI.api_key)


def extract_note_info(doc_note: str) -> dict:
    """
    Uses a GPT prompt to extract the following information from the doctor's note:
    1) the patient's weight as a float. Needed to calculate weight-dependent drug dosages.
    2) the primary diagnosis, or if absent, positive findings & abnormalities mentioned under examination
       and patient history. The RCH hospital guidelines are divided based on the diagnosis and to a much
        lesser extent, the primary symptom, e.g. abdominal pain.
        ** The extracted info is used to query the vector store and retrieve the relevant guidelines.
    3) details of a management plan. I didn't end up using this field downstream.

    """

    extract_note_info_path = os.path.join(variables.PROMPTS_DIR, "extract_note_info.txt")
    extract_note_info_prompt = open(extract_note_info_path).read()
    extract_note_info_prompt = extract_note_info_prompt.replace('{{doc_note}}', doc_note)

    print("Extracting info from doctor's note..", flush=True)
    response = CLIENT.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "system",
             "content": "You are a medical doctor and are in charge of extracting information from medical notes."},
            {
                "role": "user",
                "content": extract_note_info_prompt,
            },
        ],
        text_format=NoteInfo,
    )
    print("Extraction complete.", flush=True)
    meta_data = response.to_dict()

    json_response = json.loads(response.output_parsed.model_dump_json())
    print('Info extracted from note:\n', json_response, flush=True)

    return json_response


class NoteInfo(BaseModel):
    patients_weight: float
    diagnosis: str
    management_plan: str


def retrieve_guideline(note_info: dict) -> str:
    """
    Use a prompt containing the primary diagnosis or, if absent, the key positive findings/abnormalities to
    query the vector store and retrieve the relevant clinical guideline.

    :param note_info: dictionary containing the diagnosis or key positive findings under "diagnosis"
    :return: a string with the relevant clinical guidelines with markup.
    """

    vector_store = fetch_vector_store()
    print(f'Vector store queried: id={vector_store.id}, ',
          f'file count={vector_store.file_counts.completed}', flush=True)

    prompt_path = os.path.join(variables.PROMPTS_DIR, "find_guideline_prompt.txt")
    prompt = open(prompt_path).read()
    prompt = prompt.replace('{{diagnosis}}', note_info['diagnosis'])

    print('Retrieving guideline using vector store & LLM....(takes up to 10 secs)', flush=True)
    response = CLIENT.responses.create(
        input=prompt,
        model="gpt-4o-mini",
        tools=[{
            "type": "file_search",
            "vector_store_ids": [vector_store.id],
            "max_num_results": 3  # Each guideline doc fits into around 3 vector chunks.
        }],
        include=["file_search_call.results"]
    )

    files_found = {}
    for output in response.output:
        if not hasattr(output, 'results'):
            continue
        for result in output.results:
            if result.filename not in files_found:
                files_found[result.filename] = result.score
            elif result.score > files_found[result.filename]:
                files_found[result.filename] = result.score
            else:
                pass
    print('Vector store files found with scores', files_found, flush=True)

    if not hasattr(response.output[1], 'content'):
        result_text = None
        print('Retrieval Completed: no relevant document was found in the vector store.', flush=True)
    elif len(response.output[1].content[0].annotations) > 0:
        print('Retrieval Completed: file referenced in answer is',
              f'"{response.output[1].content[0].annotations[0].filename}"', flush=True)
        result_text = response.output[1].content[0].text
    else:
        print('Retrieval Completed', flush=True)
        result_text = response.output[1].content[0].text

    return result_text, files_found


def recalculate_dosages(result_text, patients_weight) -> str:
    """
    Converts any weight-dependent dosages found in the clinical guideline to an absolute dosage based on the
    patient's weight mentioned in the doctor's note. If the doctor's note does not mention a weight, i.e.
    weight 0.0, this conversion is skipped.
    The absolute weight is appended to the original weight-dependent dosage in the format "(total patient dose XX)"

    Example: patients_weight = 10 kg
    Input: "2 mg/kg"
    Output: "2 mg/kg (total patient dose 20 mg)"

    Note:
    The LLM agent has marked up any dosages found in the guideline in the following way. These tags
    are required to ensure the conversion is correct.

    Original text: "Dexamethasone 0.6 mg/kg (max 12 mg) PO/IM/IV"
    Marked up text:
            <drug> Dexamethasone
                <dose type="recommended" dependency="weight">
                    <value>0.6</value>
                    <unit>mg/kg</unit>
                </dose>
                (max
                <dose type="maximum">
                    <value>12</value>
                    <unit>mg</unit>
                </dose>
                )
            </drug>

    :param result_text: string containing the clinical guideline
    :param patients_weight: float representing the patient's weight
    :return: amended clinical guideline with the absolute dosages added.
    """
    if not result_text:
        return result_text

    xml_text = "<xml>"+result_text+"</xml>"
    soup = BeautifulSoup(xml_text, features="lxml")

    # if the patient's weight could not be extracted, return guideline unchanged.
    # if the result_text is None as no guidelines were found, return None.
    if not patients_weight:
        remove_xml_tags(soup)
        return str(soup)

    for dose in soup.find_all("dose"):
        # all weight-dependent dosages have the tag <dose dependency="weight">
        if dose.has_attr("dependency") and dose.get('dependency') == "weight":
            value = dose.find('value').get_text()
            value = float(value)
            new_value = value * patients_weight

            unit = dose.find('unit').get_text()
            # remove the /kg or like from the units to give non-weight dependent units,
            # e.g. "mg/kg" -> "mg"
            new_unit = re.sub("(/|per) *(kg|kilogram)", "", unit)

            new_tag = soup.new_tag('dose', type="weight")
            new_tag.string = f'(total patient dose {new_value} {new_unit})'
            dose.insert_after(new_tag)
            dose.insert_after(NavigableString(' '))  # insert a space between old and new dosage.
            print("Converting ",dose, ' --->  ', new_tag, flush=True)
    remove_xml_tags(soup)
    return str(soup)


def remove_xml_tags(soup):
    # remove all the markup tags which the LLM added
    tags_to_remove = ["dose", "drug", "value", "unit", "xml", "body", "html"]
    for tag in soup.find_all(tags_to_remove):
        tag.unwrap()
