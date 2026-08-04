import sqlite3
from datetime import datetime
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.navigationdrawer import MDNavigationDrawer, MDNavigationDrawerMenu, MDNavigationDrawerHeader, MDNavigationDrawerItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

DB_NAME = "biteflow_mobile.db"

def conectar_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def inicializar_base_datos():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingredientes (
        id_ingrediente INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        stock_actual INTEGER NOT NULL DEFAULT 0
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        precio_bs REAL NOT NULL,
        icono TEXT DEFAULT 'fastfood'
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS receta (
        id_receta INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto INTEGER,
        id_ingrediente INTEGER,
        cantidad_usada INTEGER DEFAULT 1,
        FOREIGN KEY(id_producto) REFERENCES productos(id_producto),
        FOREIGN KEY(id_ingrediente) REFERENCES ingredientes(id_ingrediente)
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        total_bs REAL NOT NULL
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mermas (
        id_merma INTEGER PRIMARY KEY AUTOINCREMENT,
        id_ingrediente INTEGER,
        cantidad INTEGER NOT NULL,
        motivo TEXT NOT NULL,
        fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY(id_ingrediente) REFERENCES ingredientes(id_ingrediente)
    );""")
    cursor.execute("SELECT COUNT(*) FROM productos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO ingredientes (nombre, stock_actual) VALUES (?, ?)", [
            ('Pan de Perro', 150), ('Salchicha Jumbo', 150),
            ('Pan de Hamburguesa', 100), ('Carne de Hamburguesa', 100),
            ('Queso (Gr)', 5000), ('Papas Ralladas (Gr)', 4000)
        ])
        cursor.executemany("INSERT INTO productos (nombre, precio_bs, icono) VALUES (?, ?, ?)", [
            ('Perro Tradicional', 100.00, 'food-hotdog'), 
            ('Hamburguesa Clásica', 160.00, 'hamburger'),
            ('Perro con Todo', 130.00, 'food-variant')
        ])
        cursor.executemany("INSERT INTO receta (id_producto, id_ingrediente, cantidad_usada) VALUES (?, ?, ?)", [
            (1, 1, 1), (1, 2, 1), (2, 3, 1), (2, 4, 1), (3, 1, 1), (3, 2, 1)  
        ])
    conn.commit()
    conn.close()

class ProductoCard(MDCard):
    def __init__(self, prod_id, nombre, precio, icono, ventas_screen, **kwargs):
        super().__init__(**kwargs)
        self.prod_id = prod_id
        self.nombre = nombre
        self.precio = precio
        self.ventas_screen = ventas_screen
        self.cantidad = 0
        self.orientation = "vertical"
        self.padding = dp(10)
        self.radius = [dp(16)]
        self.md_bg_color = (0.15, 0.15, 0.15, 1)

        row_top = MDBoxLayout(orientation="horizontal", size_hint_y=0.5, spacing=dp(5))
        row_top.add_widget(MDIconButton(icon=icono, icon_color=(0.87, 1.0, 0.6, 1)))
        lbl_info = MDBoxLayout(orientation="vertical")
        lbl_info.add_widget(MDLabel(text=nombre, font_style="Subtitle2", bold=True))
        lbl_info.add_widget(MDLabel(text=f"{precio:.2f} Bs.", font_style="Caption", theme_text_color="Secondary"))
        row_top.add_widget(lbl_info)
        self.add_widget(row_top)

        # Corregido: Removido 'alignment' que causaba el fallo
        row_bottom = MDBoxLayout(orientation="horizontal", size_hint_y=0.5, spacing=dp(5))
        self.lbl_cant = MDLabel(text="0", halign="center", font_style="H6", bold=True)
        row_bottom.add_widget(MDIconButton(icon="minus-circle-outline", on_release=self.decrementar))
        row_bottom.add_widget(self.lbl_cant)
        row_bottom.add_widget(MDIconButton(icon="plus-circle", icon_color=(0.87, 1.0, 0.6, 1), on_release=self.incrementar))
        self.add_widget(row_bottom)

    def incrementar(self, instance):
        self.cantidad += 1
        self.lbl_cant.text = str(self.cantidad)
        self.ventas_screen.actualizar_carrito(self.prod_id, self.nombre, self.precio, 1)

    def decrementar(self, instance):
        if self.cantidad > 0:
            self.cantidad -= 1
            self.lbl_cant.text = str(self.cantidad)
            self.ventas_screen.actualizar_carrito(self.prod_id, self.nombre, self.precio, -1)

    def resetear(self):
        self.cantidad = 0
        self.lbl_cant.text = "0"

class PantallaVentas(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        self.carrito = {}
        self.total = 0.0
        self.cards = []

        banner = MDCard(radius=[dp(12)], size_hint_y=0.15, md_bg_color=(0.11, 0.11, 0.11, 1), padding=dp(8))
        self.lbl_total = MDLabel(text="TOTAL: 0.00 Bs.", font_style="H4", bold=True, halign="center", text_color=(0.87, 1.0, 0.6, 1), theme_text_color="Custom")
        banner.add_widget(self.lbl_total)
        layout.add_widget(banner)

        self.grid = MDGridLayout(cols=2, spacing=dp(10), size_hint_y=0.7)
        layout.add_widget(self.grid)

        layout.add_widget(MDRaisedButton(text="CONFIRMAR COBRO (Bs.)", size_hint_x=1, size_hint_y=0.1, md_bg_color=(0.87, 1.0, 0.6, 1), text_color=(0,0,0,1), on_release=self.facturar))
        self.add_widget(layout)

    def cargar_productos(self):
        self.grid.clear_widgets()
        self.cards.clear()
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id_producto, nombre, precio_bs, icono FROM productos")
        for p_id, nom, pre, ico in cursor.fetchall():
            card = ProductoCard(p_id, nom, pre, ico, self)
            self.cards.append(card)
            self.grid.add_widget(card)
        conn.close()

    def actualizar_carrito(self, prod_id, nombre, precio, cambio):
        if prod_id in self.carrito:
            self.carrito[prod_id]['cant'] += cambio
            if self.carrito[prod_id]['cant'] <= 0: del self.carrito[prod_id]
        else:
            if cambio > 0: self.carrito[prod_id] = {'nombre': nombre, 'precio': precio, 'cant': 1}
        self.total += (precio * cambio)
        if self.total < 0: self.total = 0.0
        self.lbl_total.text = f"TOTAL: {self.total:.2f} Bs."

    def facturar(self, instance):
        if not self.carrito: return
        conn = conectar_db()
        cursor = conn.cursor()
        for p_id, data in self.carrito.items():
            cursor.execute("SELECT id_ingrediente, cantidad_usada FROM receta WHERE id_producto = ?", (p_id,))
            for ing_id, cant in cursor.fetchall():
                cursor.execute("SELECT nombre, stock_actual FROM ingredientes WHERE id_ingrediente = ?", (ing_id,))
                nom_i, st = cursor.fetchone()
                if st < (cant * data['cant']):
                    d = MDDialog(title="Sin Stock", text=f"Falta: {nom_i}", buttons=[MDFlatButton(text="OK", on_release=lambda x: d.dismiss())])
                    d.open()
                    conn.close()
                    return

        for p_id, data in self.carrito.items():
            cursor.execute("SELECT id_ingrediente, cantidad_usada FROM receta WHERE id_producto = ?", (p_id,))
            for ing_id, cant in cursor.fetchall():
                cursor.execute("UPDATE ingredientes SET stock_actual = stock_actual - ? WHERE id_ingrediente = ?", (cant * data['cant'], ing_id))
        
        cursor.execute("INSERT INTO ventas (total_bs) VALUES (?)", (self.total,))
        conn.commit()
        conn.close()

        self.carrito.clear()
        self.total = 0.0
        self.lbl_total.text = "TOTAL: 0.00 Bs."
        for card in self.cards: card.resetear()
        MDApp.get_running_app().notificar("Venta exitosa.")

class PantallaInventario(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = MDBoxLayout(orientation="vertical", padding=dp(10))
        self.add_widget(self.layout)

    def actualizar(self):
        self.layout.clear_widgets()
        self.layout.add_widget(MDLabel(text="STOCK ACTUAL", font_style="H6", halign="center", size_hint_y=0.1))
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, stock_actual FROM ingredientes")
        filas = cursor.fetchall()
        conn.close()

        tabla = MDDataTable(use_pagination=True, column_data=[("Ingrediente", dp(40)), ("Cantidad", dp(25))], row_data=filas)
        self.layout.add_widget(tabla)

class PantallaMermas(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", padding=dp(15), spacing=dp(12))
        layout.add_widget(MDLabel(text="REGISTRO DE MERMAS", font_style="H6", halign="center"))
        
        self.input_ingrediente = MDTextField(hint_text="Nombre ingrediente (Ej: Pan de Perro)", mode="rectangle")
        self.input_cantidad = MDTextField(hint_text="Cantidad perdida", mode="rectangle", input_filter="int")
        self.input_motivo = MDTextField(hint_text="Motivo (Ej: Quemado, Caido)", mode="rectangle")
        
        layout.add_widget(self.input_ingrediente)
        layout.add_widget(self.input_cantidad)
        layout.add_widget(self.input_motivo)
        layout.add_widget(MDRaisedButton(text="DESCONTAR STOCK", size_hint_x=1, md_bg_color=(0.9, 0.3, 0.3, 1), on_release=self.registrar_merma))
        
        self.container_tabla = MDBoxLayout()
        layout.add_widget(self.container_tabla)
        self.add_widget(layout)

    def actualizar(self):
        self.container_tabla.clear_widgets()
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.nombre, m.cantidad, m.motivo, m.fecha 
            FROM mermas m JOIN ingredientes i ON m.id_ingrediente = i.id_ingrediente ORDER BY m.id_merma DESC
        """)
        filas = cursor.fetchall()
        conn.close()

        tabla = MDDataTable(use_pagination=True, column_data=[("Item", dp(25)), ("Cant", dp(12)), ("Motivo", dp(20)), ("Fecha", dp(20))], row_data=filas)
        self.container_tabla.add_widget(tabla)

    def registrar_merma(self, instance):
        nom = self.input_ingrediente.text.strip()
        cant = self.input_cantidad.text.strip()
        mot = self.input_motivo.text.strip()
        if not nom or not cant or not mot: return
        
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id_ingrediente, stock_actual FROM ingredientes WHERE nombre = ?", (nom,))
        res = cursor.fetchone()
        
        if not res:
            d = MDDialog(title="Error", text="No existe ese item.", buttons=[MDFlatButton(text="OK", on_release=lambda x: d.dismiss())])
            d.open()
            conn.close()
            return
            
        ing_id, st_actual = res
        cant_i = int(cant)
        cursor.execute("UPDATE ingredientes SET stock_actual = stock_actual - ? WHERE id_ingrediente = ?", (cant_i, ing_id))
        cursor.execute("INSERT INTO mermas (id_ingrediente, cantidad, motivo) VALUES (?, ?, ?)", (ing_id, cant_i, mot))
        conn.commit()
        conn.close()
        
        self.input_ingrediente.text = ""
        self.input_cantidad.text = ""
        self.input_motivo.text = ""
        self.actualizar()
        MDApp.get_running_app().notificar("Merma registrada.")

class PantallaReportes(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = MDBoxLayout(orientation="vertical", padding=dp(10))
        self.add_widget(self.layout)

    def actualizar(self):
        self.layout.clear_widgets()
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(total_bs) FROM ventas")
        total_acumulado = cursor.fetchone()[0] or 0.0
        
        self.layout.add_widget(MDLabel(text=f"TOTAL EN CAJA:\n{total_acumulado:.2f} Bs.", font_style="H5", halign="center", size_hint_y=0.2, text_color=(0.87, 1.0, 0.6, 1), theme_text_color="Custom"))
        cursor.execute("SELECT id_venta, fecha, total_bs FROM ventas ORDER BY id_venta DESC")
        filas = cursor.fetchall()
        conn.close()

        tabla = MDDataTable(use_pagination=True, column_data=[("Factura", dp(20)), ("Fecha", dp(35)), ("Monto (Bs.)", dp(25))], row_data=filas)
        self.layout.add_widget(tabla)

class BiteFlowApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Lime"
        inicializar_base_datos()

        self.raiz = MDBoxLayout(orientation="vertical")
        
        # Agregamos el menú lateral directamente en la raíz para habilitar el gesto
        self.drawer = MDNavigationDrawer(radius=(0, dp(16), dp(16), 0))
        
        toolbar = MDTopAppBar(
            title="BiteFlow Pro", 
            anchor_title="left", 
            md_bg_color=(0.1, 0.1, 0.1, 1), 
            left_action_items=[["menu", lambda x: self.drawer.set_state("open")]]
        )
        self.raiz.add_widget(toolbar)

        self.contenedor_principal = MDBoxLayout(orientation="horizontal")
        self.sm = MDScreenManager()
        self.p_ventas = PantallaVentas(name="scr_ventas")
        self.p_inventario = PantallaInventario(name="scr_inventario")
        self.p_mermas = PantallaMermas(name="scr_mermas")
        self.p_reportes = PantallaReportes(name="scr_reportes")
        
        self.sm.add_widget(self.p_ventas)
        self.sm.add_widget(self.p_inventario)
        self.sm.add_widget(self.p_mermas)
        self.sm.add_widget(self.p_reportes)
        
        self.contenedor_principal.add_widget(self.sm)

        menu_drawer = MDNavigationDrawerMenu()
        menu_drawer.add_widget(MDNavigationDrawerHeader(title="BiteFlow", text="Menu Principal"))
        
        menu_drawer.add_widget(MDNavigationDrawerItem(icon="cash-register", text="Ventas", on_release=lambda x: self.cambiar_pantalla("scr_ventas")))
        menu_drawer.add_widget(MDNavigationDrawerItem(icon="clipboard-list", text="Inventario", on_release=lambda x: self.cambiar_pantalla("scr_inventario")))
        menu_drawer.add_widget(MDNavigationDrawerItem(icon="alert-circle", text="Mermas", on_release=lambda x: self.cambiar_pantalla("scr_mermas")))
        menu_drawer.add_widget(MDNavigationDrawerItem(icon="chart-bar", text="Reportes", on_release=lambda x: self.cambiar_pantalla("scr_reportes")))
        
        self.drawer.add_widget(menu_drawer)
        
        self.raiz.add_widget(self.contenedor_principal)
        self.raiz.add_widget(self.drawer) # El drawer se renderiza sobre el contenido
        
        self.p_ventas.cargar_productos()
        return self.raiz

    def cambiar_pantalla(self, nombre_pantalla):
        self.sm.current = nombre_pantalla
        self.drawer.set_state("close")
        if nombre_pantalla == "scr_inventario": self.p_inventario.actualizar()
        elif nombre_pantalla == "scr_mermas": self.p_mermas.actualizar()
        elif nombre_pantalla == "scr_reportes": self.p_reportes.actualizar()

    def refresh_inventario(self):
        if self.sm.current == "scr_inventario": self.p_inventario.actualizar()

    def notificar(self, texto):
        d = MDDialog(title="Aviso", text=texto, buttons=[MDRaisedButton(text="Ok", on_release=lambda x: d.dismiss())])
        d.open()

if __name__ == "__main__":
    BiteFlowApp().run()