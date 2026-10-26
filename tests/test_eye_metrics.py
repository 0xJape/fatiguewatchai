from fatiguewatch.eye_metrics import eye_aspect_ratio


def test_eye_aspect_ratio():
    assert eye_aspect_ratio([(0, 1), (1, 2), (2, 2), (4, 1), (2, 0), (1, 0)]) == 0.5
