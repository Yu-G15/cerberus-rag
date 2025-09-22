# CITS5553 RAG MVP Bundle (v2)

This bundle contains the minimal Retrieval-Augmented Generation (RAG) prototype for the CERBERUS project.  
It is organised so that each module has a clear role, and can be extended later as the pipeline evolves.

---

##  Project Structure
rag/
The core code directory of RAG (Retrieval Enhancement Generation).


data/
Store the dataset for embedding and retrieval


tests/
Automated test directory.


samples/
The sample directory can contain some test queries or sample data


assess_cases.json
The test set file defines the correspondence between query and relevant_ids, which is used to run metrics tests.


tmp_assess.json
An example DFD diagram, used for drawing/structuring.


requirements.txt
The Python dependency list of the project

## Running the Metrics Test

The test framework (`tests/test_rag_metrics.py`) evaluates the RAG module with simple queries.

1. **Activate environment**
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install pytest

2. **Export variables**

export RAG_ASSESS_FILE=assess_cases.json   # points to the evaluation queries
export RAG_TOP_K=5                         # number of docs to retrieve

3. **Run pytest**

PYTHONPATH=. pytest -q tests/test_rag_metrics.py -s

4. **Expected output**

For each query: retrieved docs, scores, hit/miss flags.

At the end: metrics such as Hit@1, Hit@3, MRR, nDCG@K, and average latency.