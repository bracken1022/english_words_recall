"""A stand-in for ExampleService in tests (spec 021), so no test talks to
a real local model."""

EXAMPLE = {"sentence": "I received a gift from my aunt.", "translation": "我收到了姨妈的礼物。"}


class FakeExampleService:
    """Replaces src.cli.session.ExampleService / ExampleService(...)."""

    def __init__(self, *_args, example=EXAMPLE, **_kwargs):
        self.example = example
        self.asked: list[str] = []

    def bind(self, _account):
        return self

    def get_or_make(self, item, timeout):
        self.asked.append(item.english)
        return dict(self.example) if self.example else None

    # The session-side interface, for web tests.
    def prepare(self, item):
        self.asked.append(item.english)

    def get(self, item):
        return dict(self.example) if self.example else None

    def status(self, item):
        return "ready" if self.example else "unavailable"

    def renew(self, item):
        return dict(self.example)


def no_examples(*args, **kwargs):
    return FakeExampleService(*args, example=None, **kwargs)
