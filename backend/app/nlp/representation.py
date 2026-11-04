"""Text representations: Bag of Words, TF-IDF (sparse) and LSA (dense).

* Bag of Words  - raw term counts per sentence.  Sparse: almost every cell is 0.
* TF-IDF        - counts re-weighted so rare, distinctive words matter more than
                  frequent ones.  Also sparse; this is what retrieval and the
                  classifier use.
* LSA           - TruncatedSVD of the TF-IDF matrix: a short *dense* vector per
                  sentence (e.g. 30 numbers, all non-zero) in which words that
                  co-occur land close together.  CPU-only, no downloads.

Neural sentence embeddings (e.g. sentence-transformers) would be another dense
option but need a model download, so they are intentionally NOT included.
"""
from __future__ import annotations

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.preprocessing import normalize

from .preprocessing import STOP_WORDS


def _doc(sentence) -> str:
    return " ".join(sentence.content_lemmas) if sentence.content_lemmas else sentence.text.lower()


def sentence_docs(sentences) -> list[str]:
    return [_doc(s) for s in sentences]


def build_tfidf(docs: list[str]):
    vec = TfidfVectorizer(lowercase=True, token_pattern=r"(?u)\b[\w\-\.]*\w\b", sublinear_tf=True)
    mat = vec.fit_transform(docs)
    return vec, mat


def describe_representations(sentences) -> dict:
    """Facts about the three representations for this transcript (computed, not assumed)."""
    docs = [d for d in sentence_docs(sentences) if d.strip()]
    if len(docs) < 2:
        return {"available": False, "reason": "Need at least two sentences."}
    bow_vec = CountVectorizer(lowercase=True, token_pattern=r"(?u)\b[\w\-\.]*\w\b")
    bow = bow_vec.fit_transform(docs)
    tf_vec, tf = build_tfidf(docs)
    terms = np.array(tf_vec.get_feature_names_out())
    weights = np.asarray(tf.max(axis=0).todense()).ravel()
    counts = np.asarray(bow.sum(axis=0)).ravel()
    top_idx = np.argsort(-weights)[:12]
    n_comp = min(30, tf.shape[1] - 1, tf.shape[0] - 1)
    lsa = None
    if n_comp >= 2:
        svd = TruncatedSVD(n_components=n_comp, random_state=42)
        dense = svd.fit_transform(tf)
        lsa = {
            "dimensions": int(n_comp),
            "explained_variance": round(float(svd.explained_variance_ratio_.sum()), 3),
            "cell_density": round(float(np.count_nonzero(dense) / dense.size), 3),
        }

    def density(m):
        return round(float(m.nnz / (m.shape[0] * m.shape[1])), 4)

    return {
        "available": True,
        "sentences": int(bow.shape[0]),
        "vocabulary_size": int(bow.shape[1]),
        "bag_of_words": {"shape": list(bow.shape), "non_zero_cells": int(bow.nnz), "density": density(bow), "type": "sparse"},
        "tfidf": {"shape": list(tf.shape), "non_zero_cells": int(tf.nnz), "density": density(tf), "type": "sparse",
                  "top_terms": [{"term": str(terms[i]), "weight": round(float(weights[i]), 3), "count": int(counts[i])}
                                for i in top_idx]},
        "lsa": ({**lsa, "type": "dense"} if lsa else None),
        "note": ("Sparse vectors have one dimension per vocabulary word and are mostly zeros; dense LSA vectors "
                 "have a few dozen dimensions that are all filled. Neural sentence embeddings are not used."),
    }


class Retriever:
    """TF-IDF cosine retrieval over transcript sentences."""

    def __init__(self, docs: list[str]):
        self.docs = docs
        self.vec, self.mat = build_tfidf(docs) if any(d.strip() for d in docs) else (None, None)

    @classmethod
    def from_sentences(cls, sentences) -> "Retriever":
        return cls(sentence_docs(sentences))

    @staticmethod
    def query_terms(question: str) -> list[str]:
        from .preprocessing import get_nlp
        nlp = get_nlp()
        if nlp is not None:
            return [t.lemma_.lower() for t in nlp(question) if not t.is_punct and not t.is_space
                    and t.lemma_.lower() not in STOP_WORDS and t.text.lower() not in STOP_WORDS]
        return [w for w in question.lower().replace("?", " ").split() if w not in STOP_WORDS]

    def search(self, question: str, k: int = 5) -> list[tuple[int, float]]:
        if self.vec is None:
            return []
        terms = self.query_terms(question)
        if not terms:
            return []
        q = self.vec.transform([" ".join(terms)])
        if q.nnz == 0:
            return []
        sims = (self.mat @ q.T).toarray().ravel()  # tf-idf rows are L2-normalised
        order = np.argsort(-sims)[:k]
        return [(int(i), float(sims[i])) for i in order if sims[i] > 0]
