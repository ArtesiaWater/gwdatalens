class DataInterface:
    def __init__(self, db=None, pstore=None, traval=None, **kwargs):
        self.db = db

        self.pstore = self.attach_pastastore(
            pstore, update_knmi=kwargs.get("update_knmi", False)
        )

        self.attach_traval(traval)

    def attach_pastastore(self, pstore, update_knmi=False):
        self.pstore = pstore
        if update_knmi:
            from pastastore.extensions import activate_hydropandas_extension

            activate_hydropandas_extension()
            self.pstore.hpd.update_knmi_meteo()

    def attach_traval(self, traval):
        self.traval = traval
