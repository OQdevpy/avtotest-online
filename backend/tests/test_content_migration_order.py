"""Ikkala jonli baza ham migratsiya qilinadi.

avtotest-tayyorlov.uz bazasida content 0011–0013 (master) qo'llangan, 0010_question_video
yo'q; prava777 bazasida esa hammasi bor. Tartib: 0009 → 0011 → 0012 → 0013 → 0010.
"""


from django.db.migrations.loader import MigrationLoader


def deps(name):
    loader = MigrationLoader(None, ignore_no_migrations=True)
    return {p.key for p in loader.graph.node_map[("content", name)].parents}


def test_lesson_banner_follows_master_order():
    assert deps("0011_lesson_banner") == {("content", "0009_answer_text_uz_blank")}


def test_question_video_is_last():
    assert deps("0010_question_video") == {("content", "0013_ticketquestion_one_ticket")}
    loader = MigrationLoader(None, ignore_no_migrations=True)
    assert loader.graph.leaf_nodes("content") == [("content", "0010_question_video")]


def test_master_history_is_consistent():
    """Master bazasidagi holat (0010 yo'q, 0011–0013 bor) izchil hisoblanadi."""
    loader = MigrationLoader(None, ignore_no_migrations=True)
    applied = {k for k in loader.graph.nodes if k != ("content", "0010_question_video")}
    for key in applied:
        for parent in loader.graph.node_map[key].parents:
            assert parent.key in applied, (key, parent.key)
