from filtros import find_contagem_match


def test_matches_contagem_with_state():
    assert find_contagem_match("Repasse destinado a Contagem, MG.") is not None


def test_matches_accented_institutional_name():
    assert find_contagem_match("Fundo Municipal de Saúde de Contagem") is not None


def test_matches_ibge_codes():
    assert find_contagem_match("Código IBGE: 3118601") is not None
    assert find_contagem_match("Município (311860)") is not None


def test_does_not_match_city_name_alone():
    assert find_contagem_match("Contagem foi citada no documento.") is None


def test_ignores_counting_false_positives_even_with_state():
    assert find_contagem_match("A contagem de casos em MG aumentou.") is None
    assert find_contagem_match("Contagem regressiva para a campanha em Minas Gerais.") is None


def test_does_not_join_city_and_state_across_sentences():
    assert find_contagem_match("Contagem foi feita. O estudo ocorreu em Minas Gerais.") is None
