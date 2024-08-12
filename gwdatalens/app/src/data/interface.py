class DataInterface:
    def __init__(self, db=None, pstore=None, traval=None):
        self.db = db
        self.pstore = pstore
        self.traval = traval

    def attach_pastastore(self, pstore):
        self.pstore = pstore

    def attach_traval(self, traval):
        self.traval = traval
