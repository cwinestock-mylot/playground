from crawler import run_crawler
from vector_store import set_up_vector_store

"""
Run this file to download all clinical guidelines from the Royal Children's Hospital Melbourne
and index them in the OpenAI vector store.
"""


def main(start_point):
    if start_point != "vector_store":
        run_crawler()

    set_up_vector_store()


if __name__ == '__main__':
    main("vector_store")
