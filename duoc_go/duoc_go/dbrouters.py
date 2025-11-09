class ProductsRouter:
    """
    Router simple:
    - App 'products_b' usa la DB 'secondary'
    - Todo lo demás usa 'default'
    """

    route_app_labels = {"products_b"}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "secondary"
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return "secondary"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        # Permitir relaciones solo dentro de la misma DB o entre apps en default
        db_obj1 = "secondary" if obj1._meta.app_label in self.route_app_labels else "default"
        db_obj2 = "secondary" if obj2._meta.app_label in self.route_app_labels else "default"
        if db_obj1 == db_obj2:
            return True
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == "secondary"
        # por defecto, otros apps van a default
        return db == "default"
