import sys
import os
import variables
import json
from datetime import datetime
from process_query import extract_note_info, retrieve_guideline, recalculate_dosages
from guardrails import validate_doc_note


def format_time(mytime):
    return mytime.replace(microsecond=0).isoformat()


if __name__ == "__main__":
    doc_note = sys.argv[1]
    start_time = datetime.now()

    print('Start time:', format_time(start_time), '\n', flush=True)
    print('############')
    print('### LOG ####')
    print('############\n')
    # check that the doctor's note is in fact a valid doctor's note
    validation_result = validate_doc_note(doc_note)
    if validation_result['is_doc_note'] is False:
        print(f"Text entered does not look like a doctor's note. "
              f"{validation_result['is_doc_note_reasoning']}. Skipping.", flush=True)

        log = {"start_time": format_time(start_time),
               "input": doc_note,
               "validation_result": validation_result
               }

    else:
        # pipeline to find the relevant guideline and calculate absolute drug dosages.
        extracted_note_info = extract_note_info(doc_note)
        result_text, _ = retrieve_guideline(extracted_note_info)
        new_result_text = recalculate_dosages(result_text, extracted_note_info['patients_weight'])

        end_time = datetime.now()
        processing_time = end_time - start_time
        print('\n\nProcessing time:', processing_time.seconds, "seconds\n", flush=True)
        print('##############', flush=True)
        print('### RESULT ###', flush=True)
        print('##############\n', flush=True)
        print(new_result_text)

        # save log to file

        log = {"start_time": format_time(start_time),
               "processing_time": str(processing_time),
               "input": doc_note,
               "output": new_result_text,
               "validation_result": validation_result,
               "extracted_note_info": extracted_note_info
               }

    time_now = format_time(datetime.now())
    output_path = os.path.join(variables.SERVER_LOG_DIR, f"{time_now}.txt")
    with open(output_path, "w") as fout:
        json.dump(log, fout, indent=4, ensure_ascii=False)
        print('\nLog of query saved to file', output_path, flush=True)
