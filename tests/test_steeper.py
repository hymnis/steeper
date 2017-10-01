import steeper


def test_classes():
    """Make sure all classes are present"""

    assert steeper.Notification
    assert steeper.Timer
    assert steeper.TreeView
    assert steeper.ListStore
    assert steeper.Controller


def test_main():
    """Make sure main function is present"""

    assert steeper.main
