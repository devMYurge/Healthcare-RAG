from datasets import load_dataset

# Login using e.g. `huggingface-cli login` to access this dataset
ds_qna = load_dataset("adrianf12/healthcare-qa-dataset")

# @dataset{healthcare_qa_2024,
#   title={Healthcare Q&A Dataset},
#   author={Adrian F},
#   year={2024},
#   publisher={Hugging Face},
#   url={https://huggingface.co/datasets/adrianf12/healthcare-qa-dataset}
# }

# Login using e.g. `huggingface-cli login` to access this dataset
ds = load_dataset("deep-div/healthcare_terms_glossary")