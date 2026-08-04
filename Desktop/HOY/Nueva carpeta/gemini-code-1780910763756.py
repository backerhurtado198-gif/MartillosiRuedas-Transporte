import sqlite3
import os
import customtkinter as ctk
from tkinter import messagebox

# ==========================================
# CONFIGURACIÓN ARQUITECTÓNICA DEL ENTORNO
# ==========================================
DB_NAME = "pos_fast_food.db"

# Paleta de colores de Alta Fidelidad
COLOR_FONDO_BASE = "#121212"
COLOR_SUPERFICIE = "#1E1E1E"
COLOR_ACENTO_LIMA = "#DEFF9A"
COLOR_TEXTO_BLANCO = "#FFFFFF"
COLOR_ALERTA_ROJO = "#FF6B6B"
COLOR_BOTON_GRIS = "#2D2D2D"

def inicializar_base_datos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Crear Tablas del Core en Bolívares
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingredientes (
        id_ingrediente INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        stock_actual INTEGER NOT NULL DEFAULT 0 CHECK(stock_actual >= 0)
    );""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        precio_bs REAL NOT NULL CHECK(precio_bs >= 0)
    );""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recetas (
        id_producto INTEGER,
        id_ingrediente INTEGER,
        cantidad INTEGER NOT NULL CHECK(cantidad > 0),
        PRIMARY KEY (id_producto, id_ingrediente),
        FOREIGN KEY (id_producto) REFERENCES productos(id_producto) ON DELETE CASCADE,
        FOREIGN KEY (id_ingrediente) REFERENCES ingredientes(id_ingrediente) ON DELETE RESTRICT
    );""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        total_bs REAL NOT NULL
    );""")
    
    # Semilla de datos con precios estimados en Bolívares
    cursor.execute("SELECT COUNT(*) FROM ingredientes")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO ingredientes (nombre, stock_actual) VALUES (?, ?)", [
            ('Pan de Perro', 60),
            ('Salchicha Jumbo', 60),
            ('Pan de Hamburguesa', 45),
            ('Carne de Hamburguesa', 45)
        ])
        cursor.executemany("INSERT INTO productos (nombre, precio_bs) VALUES (?, ?)", [
            ('Perro Tradicional', 100.00),
            ('Perro Especial', 140.00),
            ('Hamburguesa Clásica', 160.00),
            ('Hamburguesa Doble', 220.00)
        ])
        cursor.executemany("INSERT INTO recetas (id_producto, id_ingrediente, cantidad) VALUES (?, ?, ?)", [
            (1, 1, 1), (1, 2, 1),  # Perro Tradicional
            (2, 1, 1), (2, 2, 1),  # Perro Especial
            (3, 3, 1), (3, 4, 1),  # Hamburguesa Clásica
            (4, 3, 1), (4, 4, 2)   # Hamburguesa Doble usa 2 carnes
        ])
    conn.commit()
    conn.close()

# ==========================================
# INTERFAZ DE USUARIO DE ALTA FIDELIDAD (UI)
# ==========================================
class ModernPOSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("POS Comida Rápida - Facturación en Bs.")
        self.root.geometry("1280x720")
        self.root.configure(fg_color=COLOR_FONDO_BASE)
        
        ctk.set_appearance_mode("dark")
        
        # Estados lógicos internos
        self.carrito = {} 
        self.pedidos_cocina = []
        self.ingrediente_seleccionado_id = None
        self.val_entrada = ctk.StringVar(value="")
        self.total_actual_bs = 0.0
        
        # 1. BARRA SUPERIOR DE CONTROL (Header)
        self.header = ctk.CTkFrame(self.root, height=60, fg_color=COLOR_SUPERFICIE, corner_radius=0)
        self.header.pack(side=ctk.TOP, fill=ctk.X)
        
        lbl_logo = ctk.CTkLabel(self.header, text="FAST FOOD POS", font=ctk.CTkFont(family="Arial", size=20, weight="bold"), text_color=COLOR_TEXTO_BLANCO)
        lbl_logo.pack(side=ctk.LEFT, padx=20)
        
        lbl_status = ctk.CTkLabel(self.header, text="● MONEDA: BOLÍVARES (Bs.)", font=ctk.CTkFont(family="Arial", size=14, weight="bold"), text_color=COLOR_ACENTO_LIMA)
        lbl_status.pack(side=ctk.RIGHT, padx=30)
        
        # 2. CONTENEDOR CENTRAL DE PESTAÑAS (Tabview)
        self.tabview = ctk.CTkTabview(self.root, segmented_button_selected_color=COLOR_ACENTO_LIMA, segmented_button_selected_hover_color="#c2e078", segmented_button_unselected_color=COLOR_BOTON_GRIS, text_color=COLOR_TEXTO_BLANCO)
        self.tabview.pack(fill=ctk.BOTH, expand=True, padx=15, pady=10)
        
        self.tab_ventas = self.tabview.add("   Ventas   ")
        self.tab_inventario = self.tabview.add("   Cargar Inventario   ")
        self.tab_cocina = self.tabview.add("   Cola de Cocina   ")
        self.tab_cierre = self.tabview.add("   Cierre de Caja   ")
        
        # Configurar color de fondo interno de las pestañas
        self.tab_ventas.configure(fg_color=COLOR_FONDO_BASE)
        self.tab_inventario.configure(fg_color=COLOR_FONDO_BASE)
        self.tab_cocina.configure(fg_color=COLOR_FONDO_BASE)
        self.tab_cierre.configure(fg_color=COLOR_FONDO_BASE)
        
        # Inicializar Módulos Visuales
        self.build_modulo_ventas()
        self.build_modulo_inventario()
        self.build_modulo_cocina()
        
        # Escuchar cambios de pestaña para recargas en tiempo real
        self.tabview.configure(command=self.on_tab_changed)

    # --------------------------------------
    # MÓDULO 1: INTERFAZ DE VENTAS
    # --------------------------------------
    def build_modulo_ventas(self):
        # Panel Izquierdo: Carrito Digital Fijo
        self.panel_carrito = ctk.CTkFrame(self.tab_ventas, width=380, fg_color=COLOR_SUPERFICIE, corner_radius=12)
        self.panel_carrito.pack(side=ctk.LEFT, fill=ctk.Y, padx=(0, 10), pady=10)
        self.panel_carrito.pack_propagate(False)
        
        ctk.CTkLabel(self.panel_carrito, text="ORDEN ACTUAL", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_ACENTO_LIMA).pack(pady=15)
        
        self.scroll_carrito = ctk.CTkScrollableFrame(self.panel_carrito, fg_color="#181818", corner_radius=8)
        self.scroll_carrito.pack(fill=ctk.BOTH, expand=True, padx=15, pady=5)
        
        # Panel Inferior de Totales en Bs.
        panel_totales = ctk.CTkFrame(self.panel_carrito, fg_color="transparent")
        panel_totales.pack(side=ctk.BOTTOM, fill=ctk.X, padx=15, pady=15)
        
        self.lbl_total_bs = ctk.CTkLabel(panel_totales, text="TOTAL: 0.00 Bs.", font=ctk.CTkFont(size=26, weight="bold"), text_color=COLOR_ACENTO_LIMA)
        self.lbl_total_bs.pack(pady=10)
        
        self.btn_pagar = ctk.CTkButton(panel_totales, text="✔ CONFIRMAR VENTA (Bs.)", font=ctk.CTkFont(size=14, weight="bold"), fg_color=COLOR_ACENTO_LIMA, text_color="#000000", hover_color="#c2e078", height=55, corner_radius=8, command=self.procesar_pago_digital)
        self.btn_pagar.pack(fill=ctk.X, pady=5)
        
        self.btn_vaciar = ctk.CTkButton(panel_totales, text="Vaciar Orden", font=ctk.CTkFont(size=11), fg_color="transparent", text_color=COLOR_ALERTA_ROJO, hover_color="#2a1a1a", command=self.vaciar_orden)
        self.btn_vaciar.pack(pady=2)

        # Panel Derecho: Grilla Táctil de Productos
        self.panel_productos = ctk.CTkFrame(self.tab_ventas, fg_color=COLOR_SUPERFICIE, corner_radius=12)
        self.panel_productos.pack(side=ctk.RIGHT, fill=ctk.BOTH, expand=True, pady=10)
        
        ctk.CTkLabel(self.panel_productos, text="MENÚ DISPONIBLE", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXTO_BLANCO).pack(pady=15)
        
        self.grid_items = ctk.CTkFrame(self.panel_productos, fg_color="transparent")
        self.grid_items.pack(fill=ctk.BOTH, expand=True, padx=20, pady=10)
        
        self.renderizar_botones_menu()

    def renderizar_botones_menu(self):
        for widget in self.grid_items.winfo_children():
            widget.destroy()
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id_producto, nombre, precio_bs FROM productos")
        items = cursor.fetchall()
        conn.close()
        
        r, c = 0, 0
        for p_id, p_nom, p_pre in items:
            btn = ctk.CTkButton(self.grid_items, text=f"{p_nom}\n\n{p_pre:.2f} Bs.", font=ctk.CTkFont(size=13, weight="bold"), fg_color=COLOR_BOTON_GRIS, text_color=COLOR_TEXTO_BLANCO, hover_color="#3d3d3d", width=160, height=120, corner_radius=10, command=lambda idx=p_id: self.agregar_item_carrito(idx))
            btn.grid(row=r, column=c, padx=12, pady=12)
            c += 1
            if c > 3:
                c = 0
                r += 1

    def agregar_item_carrito(self, prod_id):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, precio_bs FROM productos WHERE id_producto = ?", (prod_id,))
        res = cursor.fetchone()
        conn.close()
        
        if res:
            nom, pre = res
            if prod_id in self.carrito:
                self.carrito[prod_id]["cant"] += 1
            else:
                self.carrito[prod_id] = {"nombre": nom, "precio": pre, "cant": 1}
            self.actualizar_render_carrito()

    def vaciar_orden(self):
        self.carrito.clear()
        self.actualizar_render_carrito()

    def actualizar_render_carrito(self):
        for widget in self.scroll_carrito.winfo_children():
            widget.destroy()
            
        total_bs = 0.0
        for pid, data in self.carrito.items():
            subtotal = data["precio"] * data["cant"]
            total_bs += subtotal
            
            item_row = ctk.CTkFrame(self.scroll_carrito, fg_color="transparent")
            item_row.pack(fill=ctk.X, pady=4)
            
            lbl_info = ctk.CTkLabel(item_row, text=f"{data['cant']}x {data['nombre']}\n{subtotal:.2f} Bs.", font=ctk.CTkFont(size=12), text_color=COLOR_TEXTO_BLANCO, justify=ctk.LEFT, anchor=ctk.W)
            lbl_info.pack(side=ctk.LEFT, padx=5)
            
            btn_eliminar = ctk.CTkButton(item_row, text="🗑", width=26, height=26, fg_color="transparent", text_color=COLOR_ALERTA_ROJO, hover_color="#2d2d2d", command=lambda idx=pid: self.reducir_o_eliminar(idx))
            btn_eliminar.pack(side=ctk.RIGHT, padx=5)
            
        self.lbl_total_bs.configure(text=f"TOTAL: {total_bs:.2f} Bs.")
        self.total_actual_bs = total_bs

    def reducir_o_eliminar(self, pid):
        if pid in self.carrito:
            if self.carrito[pid]["cant"] > 1:
                self.carrito[pid]["cant"] -= 1
            else:
                del self.carrito[pid]
        self.actualizar_render_carrito()

    def procesar_pago_digital(self):
        if not self.carrito:
            messagebox.showwarning("Orden Vacía", "Seleccione productos antes de confirmar el pago.")
            return
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        for pid, data in self.carrito.items():
            cursor.execute("SELECT id_ingrediente, cantidad FROM recetas WHERE id_producto = ?", (pid,))
            for ing_id, font_nec in cursor.fetchall():
                total_necesitado = font_nec * data["cant"]
                cursor.execute("SELECT nombre, stock_actual FROM ingredientes WHERE id_ingrediente = ?", (ing_id,))
                res_ing = cursor.fetchone()
                if res_ing:
                    ing_nom, stock_act = res_ing
                    if stock_act < total_necesitado:
                        messagebox.showerror("ALERTA DE INVENTARIO", f"Imposible procesar: '{ing_nom}' insuficiente.\nEn Stock: {stock_act} unidades.")
                        conn.close()
                        return
        
        cursor.execute("BEGIN TRANSACTION;")
        try:
            cursor.execute("INSERT INTO ventas (total_bs) VALUES (?)", (self.total_actual_bs,))
            id_v = cursor.lastrowid
            
            items_pedido = []
            for pid, data in self.carrito.items():
                cursor.execute("SELECT id_ingrediente, cantidad FROM recetas WHERE id_producto = ?", (pid,))
                for ing_id, cant_nec in cursor.fetchall():
                    cursor.execute("UPDATE ingredientes SET stock_actual = stock_actual - ? WHERE id_ingrediente = ?", (cant_nec * data["cant"], ing_id))
                items_pedido.append(f"{data['cant']}x {data['nombre']}")
                
            cursor.execute("COMMIT;")
            
            self.pedidos_cocina.append({"id": id_v, "items": ", ".join(items_pedido)})
            messagebox.showinfo("VENTA REGISTRADA", f"Procesada con éxito.\nTotal cobrado: {self.total_actual_bs:.2f} Bs.")
            self.vaciar_orden()
        except Exception as e:
            cursor.execute("ROLLBACK;")
            messagebox.showerror("Error Crítico", f"Fallo de persistencia local: {str(e)}")
        finally:
            conn.close()

    # --------------------------------------
    # MÓDULO 2: GESTIÓN DE INVENTARIOS
    # --------------------------------------
    def build_modulo_inventario(self):
        self.panel_inv_izq = ctk.CTkFrame(self.tab_inventario, fg_color=COLOR_SUPERFICIE, corner_radius=12)
        self.panel_inv_izq.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=(0, 10), pady=10)
        
        ctk.CTkLabel(self.panel_inv_izq, text="SELECCIONE MATERIA PRIMA", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXTO_BLANCO).pack(pady=15)
        
        self.scroll_inventario = ctk.CTkScrollableFrame(self.panel_inv_izq, fg_color="transparent")
        self.scroll_inventario.pack(fill=ctk.BOTH, expand=True, padx=15, pady=5)
        
        frame_field = ctk.CTkFrame(self.panel_inv_izq, fg_color="transparent")
        frame_field.pack(side=ctk.BOTTOM, fill=ctk.X, padx=20, pady=20)
        
        ctk.CTkLabel(frame_field, text="Cantidad a Cargar:", font=ctk.CTkFont(size=14)).pack(side=ctk.LEFT, padx=10)
        self.entry_inv = ctk.CTkEntry(frame_field, textvariable=self.val_entrada, font=ctk.CTkFont(size=22, weight="bold"), width=140, height=45, justify=ctk.CENTER, fg_color="#111", text_color=COLOR_ACENTO_LIMA, border_color=COLOR_BOTON_GRIS)
        self.entry_inv.pack(side=ctk.LEFT, padx=10)
        
        btn_guardar_stock = ctk.CTkButton(frame_field, text="💾 CARGAR", font=ctk.CTkFont(size=14, weight="bold"), fg_color=COLOR_ACENTO_LIMA, text_color="#000", width=120, height=45, command=self.guardar_entrada_stock)
        btn_guardar_stock.pack(side=ctk.RIGHT, padx=10)
        
        self.renderizar_lista_inventario()

        self.panel_inv_der = ctk.CTkFrame(self.tab_inventario, width=360, fg_color=COLOR_SUPERFICIE, corner_radius=12)
        self.panel_inv_der.pack(side=ctk.RIGHT, fill=ctY if 'ctY' in globals() else ctk.Y, pady=10)
        self.panel_inv_der.pack_propagate(False)
        
        ctk.CTkLabel(self.panel_inv_der, text="TECLADO TÁCTIL", font=ctk.CTkFont(size=12, weight="bold"), text_color="#666").pack(pady=15)
        
        frame_pad = ctk.CTkFrame(self.panel_inv_der, fg_color="transparent")
        frame_pad.pack(expand=True)
        
        botones = ['7', '8', '9', '4', '5', '6', '1', '2', '3', '0', '00', '⌫']
        r, c = 0, 0
        for b_txt in botones:
            cmd = lambda tx=b_txt: self.click_numpad(tx)
            btn_pad = ctk.CTkButton(frame_pad, text=b_txt, font=ctk.CTkFont(size=18, weight="bold"), fg_color=COLOR_BOTON_GRIS, text_color=COLOR_TEXTO_BLANCO, hover_color="#444", width=75, height=65, corner_radius=8, command=cmd)
            btn_pad.grid(row=r, column=c, padx=6, pady=6)
            c += 1
            if c > 2:
                c = 0
                r += 1

    def renderizar_lista_inventario(self):
        for widget in self.scroll_inventario.winfo_children():
            widget.destroy()
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id_ingrediente, nombre, stock_actual FROM ingredientes")
        rows = cursor.fetchall()
        conn.close()
        
        for ing_id, nom, stk in rows:
            is_selected = (self.ingrediente_seleccionado_id == ing_id)
            bg = COLOR_ACENTO_LIMA if is_selected else COLOR_BOTON_GRIS
            fg = "#000000" if is_selected else COLOR_TEXTO_BLANCO
            
            btn_row = ctk.CTkButton(self.scroll_inventario, text=f" 📦  {nom.ljust(25)} [ Stock Actual: {stk} Unidades ]", font=ctk.CTkFont(family="Courier", size=13, weight="bold"), fg_color=bg, text_color=fg, hover_color="#3a3a3a" if not is_selected else COLOR_ACENTO_LIMA, anchor=ctk.W, height=45, corner_radius=6, command=lambda idx=ing_id: self.seleccionar_ingrediente(idx))
            btn_row.pack(fill=ctk.X, pady=4, padx=5)

    def seleccionar_ingrediente(self, idx):
        self.ingrediente_seleccionado_id = idx
        self.renderizar_lista_inventario()

    def click_numpad(self, valor):
        act = self.val_entrada.get()
        if valor == '⌫':
            self.val_entrada.set(act[:-1])
        elif valor == '00':
            self.val_entrada.set(act + "00")
        else:
            self.val_entrada.set(act + valor)

    def guardar_entrada_stock(self):
        if not self.ingrediente_seleccionado_id:
            messagebox.showwarning("Selección Faltante", "Toque primero un ingrediente de la lista para cargarlo.")
            return
        try:
            val = int(self.val_entrada.get())
            if val <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error numérico", "Ingrese un valor entero válido en el teclado.")
            return
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE ingredientes SET stock_actual = stock_actual + ? WHERE id_ingrediente = ?", (val, self.ingrediente_seleccionado_id))
        conn.commit()
        conn.close()
        
        messagebox.showinfo("INVENTARIO ACTUALIZADO", "Carga inyectada con éxito en los registros locales.")
        self.val_entrada.set("")
        self.renderizar_lista_inventario()

    # --------------------------------------
    # MÓDULO 3: COLA DIGITAL DE COCINA
    # --------------------------------------
    def build_modulo_cocina(self):
        self.scroll_cocina = ctk.CTkScrollableFrame(self.tab_cocina, fg_color=COLOR_SUPERFICIE, corner_radius=12)
        self.scroll_cocina.pack(fill=ctk.BOTH, expand=True, padx=15, pady=15)
        self.renderizar_cola_cocina()

    def renderizar_cola_cocina(self):
        for widget in self.scroll_cocina.winfo_children():
            widget.destroy()
            
        if not self.pedidos_cocina:
            lbl_vacio = ctk.CTkLabel(self.scroll_cocina, text="-- COLA DIGITAL VACÍA --\nTodos los pedidos han sido servidos.", font=ctk.CTkFont(size=14), text_color="#555")
            lbl_vacio.pack(pady=100)
            return
            
        for idx, item_p in enumerate(self.pedidos_cocina):
            card = ctk.CTkFrame(self.scroll_cocina, fg_color="#1a1a1a", border_width=1, border_color=COLOR_BOTON_GRIS, corner_radius=8)
            card.pack(fill=ctk.X, pady=6, padx=10)
            
            ctk.CTkLabel(card, text=f"ORDEN #{item_p['id']}", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_ACENTO_LIMA).pack(side=ctk.LEFT, padx=20, pady=15)
            ctk.CTkLabel(card, text=item_p['items'], font=ctk.CTkFont(size=13), text_color=COLOR_TEXTO_BLANCO, anchor=ctk.W).pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=10)
            
            btn_despachar = ctk.CTkButton(card, text="✔ ENTREGADO", font=ctk.CTkFont(size=12, weight="bold"), fg_color="#27AE60", text_color="#fff", hover_color="#219653", width=110, height=36, command=lambda i=idx: self.eliminar_pedido_cocina(i))
            btn_despachar.pack(side=ctk.RIGHT, padx=20)

    def eliminar_pedido_cocina(self, index):
        del self.pedidos_cocina[index]
        self.renderizar_cola_cocina()

    # --------------------------------------
    # MÓDULO 4: RENDIMIENTO Y CIERRE FINANCIERO
    # --------------------------------------
    def renderizar_modulo_cierre(self):
        for widget in self.tab_cierre.winfo_children():
            widget.destroy()
            
        frame_reporte = ctk.CTkFrame(self.tab_cierre, fg_color=COLOR_SUPERFICIE, corner_radius=12)
        frame_reporte.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame_reporte, text="CUADRE DE CAJA OPERATIVO (NATIVO BS.)", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXTO_BLANCO).pack(pady=20)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(total_bs), COUNT(*) FROM ventas WHERE date(fecha) = date('now', 'localtime')")
        total_rec, count_rec = cursor.fetchone()
        total_rec = total_rec if total_rec else 0.0
        count_rec = count_rec if count_rec else 0
        
        txt_informe = f"RESUMEN OPERATIVO DE HOY:\n" \
                      f"--------------------------------------------\n" \
                      f"• Facturas Emitidas:        {count_rec} órdenes\n" \
                      f"• Total Contabilizado (Bs):  {total_rec:.2f} Bs.\n"
                      
        ctk.CTkLabel(frame_reporte, text=txt_informe, font=ctk.CTkFont(family="Courier", size=14, weight="bold"), text_color=COLOR_TEXTO_BLANCO, justify=ctk.LEFT).pack(anchor=ctk.W, padx=40, pady=10)
        
        ctk.CTkLabel(frame_reporte, text="MONITOR DE ALERTA DE INGREDIENTES:", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_ACENTO_LIMA).pack(anchor=ctk.W, padx=40, pady=(20, 5))
        
        cursor.execute("SELECT nombre, stock_actual FROM ingredientes")
        for nom, stk in cursor.fetchall():
            clr = COLOR_TEXTO_BLANCO
            warn = ""
            if stk <= 15:
                clr = COLOR_ALERTA_ROJO
                warn = " ⚠️ [CRÍTICO - REABASTECER]"
                
            ctk.CTkLabel(frame_reporte, text=f"  - {nom.ljust(22)}: {stk} unidades{warn}", font=ctk.CTkFont(family="Courier", size=12, weight="bold"), text_color=clr).pack(anchor=ctk.W, padx=60)
            
        conn.close()
        
        btn_cerrar = ctk.CTkButton(frame_reporte, text="🔒 CONSOLIDAR Y APAGAR SISTEMA", font=ctk.CTkFont(size=14, weight="bold"), fg_color=COLOR_ALERTA_ROJO, text_color="#fff", hover_color="#c0392b", height=45, command=self.cerrar_sistema_seguro)
        btn_cerrar.pack(side=ctk.BOTTOM, fill=ctk.X, padx=40, pady=30)

    def cerrar_sistema_seguro(self):
        if messagebox.askyesno("CONFIRMAR", "¿Dar por terminada la jornada de ventas?\nLa base de datos SQLite se indexará automáticamente."):
            self.root.quit()

    # Interceptor de navegación reactivo
    def on_tab_changed(self):
        sel = self.tabview.get()
        if "Ventas" in sel:
            self.renderizar_botones_menu()
            self.actualizar_render_carrito()
        elif "Inventario" in sel:
            self.renderizar_lista_inventario()
        elif "Cocina" in sel:
            self.renderizar_cola_cocina()
        elif "Cierre" in sel:
            self.renderizar_modulo_cierre()

# ==========================================
# GESTOR DE ARRANQUE
# ==========================================
if __name__ == "__main__":
    inicializar_base_datos()
    root = ctk.CTk()
    app = ModernPOSApp(root)
    root.mainloop()