from infraagentkit.knowledge import KnowledgeIndex, load_packs
from infraagentkit.text import has_term, tokens
from infraagentkit.tools import risk_assess


def test_latin_terms_match_on_word_boundaries():
    assert has_term("Worker near the edge", "edge")
    assert not has_term("I have no knowledge", "edge")
    assert not has_term("encroachment of the site", "ncr")
    assert has_term("NCR-0042 raised", "ncr")


def test_chinese_terms_match_as_substrings_and_index_as_bigrams():
    assert has_term("工人在临边作业", "临边")
    assert "临边" in tokens("工人在临边作业") and "边作" in tokens("工人在临边作业")


def test_stopwords_alone_retrieve_nothing():
    index = KnowledgeIndex(load_packs())
    assert index.search("I have no knowledge of this site, just saying hello") == []
    assert index.search("会议改到周五下午") == []


def test_bilingual_retrieval_finds_the_same_source():
    index = KnowledgeIndex(load_packs())
    assert index.search("Concrete crack on pier, NCR needed")[0]["ref"] == "QA-NCR-001"
    assert index.search("墩柱混凝土裂缝需开具不符合项")[0]["ref"] == "QA-NCR-001"


def test_every_source_has_a_content_digest():
    assert all(len(s.digest) == 64 for s in load_packs())


def test_risk_signals_use_word_boundaries():
    assert risk_assess("Pledge to acknowledge the edgeless design")["risk"] == "LOW"
    assert risk_assess("Lifting with a mobile crane")["risk"] == "HIGH"
    assert risk_assess("人员坠落，现场封闭")["risk"] == "CRITICAL"
