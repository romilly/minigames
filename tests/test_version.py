import version


def test_the_version_is_major_minor_patch():
    parts = version.__version__.split('.')
    assert len(parts) == 3 and all(p.isdigit() for p in parts)
