def evaluate_result(result_text: str,
                    truth: dict,
                    extracted_note_info: dict,
                    files_found: dict
                    ) -> dict:
    eval_result = {}

    if truth['patients_weight'] == extracted_note_info['patients_weight']:
        correctness = True
    else:
        correctness = False

    eval_result['patient_weight'] = {'correct': correctness,
                                     'predicted': extracted_note_info['patients_weight'],
                                     'truth': truth['patients_weight']}

    present_strings = set()
    missing_strings = set()
    for string in truth['obligatory_strings']:
        if result_text and string.lower() in result_text.lower():
            present_strings.add(string)
        else:
            missing_strings.add(string)
    if len(missing_strings) == 0:
        correct = True
    else:
        correct = False

    eval_result['obligatory_strings'] = {"correct": correct,
                                         "found": sorted(list(present_strings)),
                                         "missing": sorted(list(missing_strings))}

    file_found = False
    if truth['relevant_file'] and truth['relevant_file'] in files_found:
        file_found = True
    eval_result['relevant_file_found'] = file_found

    eval_result['output_text'] = result_text

    return eval_result
