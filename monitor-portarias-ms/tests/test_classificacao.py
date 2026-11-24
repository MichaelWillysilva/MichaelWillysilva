from filtros import classify_document, classify_relevance, classify_type, extract_deadline
from fontes.base import Document


FILTERS = {
    "ibge_codes": ["3118601", "311860"],
    "institutional_terms": [
        "Prefeitura Municipal de Contagem",
        "Fundo Municipal de Saúde de Contagem",
    ],
    "state_terms": ["MG", "Minas Gerais"],
    "municipal_scope_terms": [
        "financiamento da atenção primária à saúde",
        "todos os municípios brasileiros",
    ],
    "bh_region_terms": ["Região Metropolitana de Belo Horizonte", "RMBH"],
}


def test_relevance_is_high_for_contagem_and_ibge():
    assert classify_relevance("Fundo Municipal de Saúde de Contagem", FILTERS) == "alta"
    assert classify_relevance("IBGE 3118601", FILTERS) == "alta"


def test_relevance_is_medium_for_universal_and_bh_region_policies():
    assert (
        classify_relevance("Financiamento da Atenção Primária à Saúde", FILTERS)
        == "média"
    )
    assert classify_relevance("Municípios da RMBH", FILTERS) == "média"


def test_relevance_is_low_for_unrelated_content():
    assert classify_relevance("Regras gerais para hospitais federais", FILTERS) == "baixa"


def test_anvisa_records_are_kept_for_configured_topics():
    document = Document(
        title="RDC para serviços de saúde",
        url="https://example.org/rdc",
        summary="Regulamenta serviços de saúde.",
    )
    result = classify_document(
        document,
        "Regulamenta os serviços de saúde em todo o Brasil.",
        "anvisa",
        {"filters": FILTERS, "themes": {"Serviços de saúde": ["serviços de saúde"]}},
    )
    assert result is not None
    assert result["relevance"] == "baixa"
    assert result["theme"] == ["Serviços de saúde"]


def test_type_uses_requested_categories():
    assert classify_type("Aprova repasse financeiro") == "repasse"
    assert classify_type("Resolução da Diretoria Colegiada") == "regulamentação"
    assert classify_type("Pactuação na CIB-SUS") == "pactuação"


def test_extracts_deadline_date_or_duration():
    assert extract_deadline("Prazo final em 30/12/2026.") == "2026-12-30"
    assert extract_deadline("Vigência de 12 meses.") == "12 meses"
