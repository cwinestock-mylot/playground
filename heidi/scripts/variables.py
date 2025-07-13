import os
from openai import OpenAI

#OpenAI.api_key
OPENAI_MODEL_SEARCH = "gpt-4o-mini"

DATA_DIR = "../data"
TEST_CASES_DIR = os.path.join(DATA_DIR, 'test_cases')
CLEANED_DOCS_DIR = os.path.join(DATA_DIR, 'cleaned_docs')
RAW_DOCS_DIR = os.path.join(DATA_DIR, 'raw_docs')
PROMPTS_DIR = "../prompts"
OUTPUT_DIR = "../output"
SERVER_LOG_DIR = os.path.join(OUTPUT_DIR, 'server_log')
EVAL_RESULTS_PATH = os.path.join(OUTPUT_DIR, 'eval_results.json')
