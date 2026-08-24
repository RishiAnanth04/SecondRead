"""Quick smoke-test / usage example."""
from pipeline import PhenotypeExtractor

NOTE = """
Patient presents with productive cough and shortness of breath.
No fever. History of chronic otitis media and sinusitis.
Hemoglobin: 8.2 g/dL. Denies chest pain. Bilateral hearing loss noted.
Started on ibuprofen 200 mg PO BID for pain. Family history of scoliosis.
"""

if __name__ == "__main__":
    extractor = PhenotypeExtractor.from_obo("hp.obo")  # downloads hp.obo if missing
    spans = extractor.extract(NOTE)
    for s in spans:
        print(s)
