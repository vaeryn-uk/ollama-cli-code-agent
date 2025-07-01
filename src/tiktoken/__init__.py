class _Encoding:
    def encode(self, text):
        return text.split()


def encoding_for_model(model):
    return _Encoding()


def get_encoding(name):
    return _Encoding()
