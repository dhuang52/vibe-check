class User:
    def __init__(self, id, created_at):
        self.id = id
        self.created_at = created_at

    def __str__(self):
        return f'{self.id}: {self.created_at}'
