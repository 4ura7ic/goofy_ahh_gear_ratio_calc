import tkinter as tk
from tkinter import ttk, filedialog
import tkinter.font as tkfont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from gear_logic import MAX_GEARS, MIN_RPM, calc_wheel_diameter_m, gear_speed_table, export_csv

# ---- Custom Error Popup ----
def custom_error_popup(parent, title, msg, width=600, height=300):
    err = tk.Toplevel(parent)
    err.title(title)
    err.geometry(f"{width}x{height}")
    err.resizable(False, False)
    err.transient(parent)
    err.grab_set()
    err.protocol("WM_DELETE_WINDOW", lambda: err.destroy())
    ttk.Label(err, text=title, font=("Segoe UI", 13, "bold")).pack(pady=(18, 5))
    ttk.Label(err, text=msg, font=("Segoe UI", 11), wraplength=width-40, justify="center").pack(pady=(0, 15))
    ttk.Button(err, text="OK", width=12, command=err.destroy).pack(pady=(0, 16))
    err.wait_window()

class GearRatioWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Goofy Ahh Gear Ratio Calculator")
        self.geometry("900x700")
        self.minsize(700, 600)
        self.resizable(True, True)
        self.state = {}
        self.frames = []
        self.current = 0
        self.init_steps()
        self.show_step(0)

    def init_steps(self):
        self.frames = [
            TireStep(self, self.state, self.next_step),
            DrivetrainStep(self, self.state, self.next_step, self.prev_step),
            GearRatiosStep(self, self.state, self.next_step, self.prev_step),
            OutputStep(self, self.state, self.show_results, self.prev_step),
            ResultsStep(self, self.state),
        ]
        for frame in self.frames:
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def show_step(self, idx):
        for i, frame in enumerate(self.frames):
            frame.tkraise() if i == idx else frame.lower()
        self.current = idx

    def next_step(self):
        self.show_step(self.current + 1)

    def prev_step(self):
        self.show_step(self.current - 1)

    def show_results(self):
        self.frames[4].update_results()
        self.show_step(4)

    def reset_all(self):
        self.state.clear()
        for frame in self.frames:
            if hasattr(frame, 'reset'):
                frame.reset()

    def reset_partial(self):
        for frame in self.frames:
            if hasattr(frame, 'refresh_entries'):
                frame.refresh_entries()

class TireStep(ttk.Frame):
    def __init__(self, master, state, next_callback):
        super().__init__(master)
        self.state = state
        self.next_callback = next_callback
        self.tire_method = tk.StringVar(value="specs")
        label = ttk.Label(self, text="Step 1: Tire Info", font=("Segoe UI", 16))
        label.pack(pady=15)
        method_frame = ttk.Frame(self)
        method_frame.pack(pady=10)
        ttk.Radiobutton(method_frame, text="Width / Aspect Ratio / Rim", variable=self.tire_method, value="specs", command=self.switch_fields).grid(row=0, column=0, padx=10)
        ttk.Radiobutton(method_frame, text="Direct Diameter", variable=self.tire_method, value="diameter", command=self.switch_fields).grid(row=0, column=1, padx=10)
        self.frame_specs = ttk.Frame(self)
        ttk.Label(self.frame_specs, text="Tire Width (mm):").grid(row=0, column=0, sticky='e')
        self.entry_width = ttk.Entry(self.frame_specs, width=10)
        self.entry_width.grid(row=0, column=1)
        ttk.Label(self.frame_specs, text="Aspect Ratio (%):").grid(row=1, column=0, sticky='e')
        self.entry_aspect = ttk.Entry(self.frame_specs, width=10)
        self.entry_aspect.grid(row=1, column=1)
        ttk.Label(self.frame_specs, text="Rim Diameter (in):").grid(row=2, column=0, sticky='e')
        self.entry_rim = ttk.Entry(self.frame_specs, width=10)
        self.entry_rim.grid(row=2, column=1)
        self.frame_diameter = ttk.Frame(self)
        ttk.Label(self.frame_diameter, text="Tire Diameter:").grid(row=0, column=0, sticky='e')
        self.entry_diameter = ttk.Entry(self.frame_diameter, width=10)
        self.entry_diameter.grid(row=0, column=1)
        self.unit_var = tk.StringVar(value="in")
        ttk.Radiobutton(self.frame_diameter, text="inches", variable=self.unit_var, value="in").grid(row=0, column=2)
        ttk.Radiobutton(self.frame_diameter, text="mm", variable=self.unit_var, value="mm").grid(row=0, column=3)
        self.frame_specs.pack(pady=10)
        next_btn = ttk.Button(self, text="Next →", command=self.on_next)
        next_btn.pack(pady=25)

    def switch_fields(self):
        if self.tire_method.get() == "specs":
            self.frame_diameter.pack_forget()
            self.frame_specs.pack(pady=10)
        else:
            self.frame_specs.pack_forget()
            self.frame_diameter.pack(pady=10)

    def reset(self):
        self.entry_width.delete(0, 'end')
        self.entry_aspect.delete(0, 'end')
        self.entry_rim.delete(0, 'end')
        self.entry_diameter.delete(0, 'end')
        self.tire_method.set("specs")
        self.unit_var.set("in")
        self.switch_fields()

    def on_next(self):
        try:
            if self.tire_method.get() == "specs":
                width = float(self.entry_width.get())
                aspect = float(self.entry_aspect.get())
                rim = float(self.entry_rim.get())
                # Validate inputs
                if width <= 0 or aspect <= 0 or rim <= 0:
                    raise ValueError("All fields must be positive numbers.")
                diameter_m = calc_wheel_diameter_m('specs', width=width, aspect=aspect, rim=rim)
            else:
                val = float(self.entry_diameter.get())
                if val <= 0:
                    raise ValueError("Tire diameter must be a positive number.")
                diameter_m = calc_wheel_diameter_m('diameter', diameter=val, unit=self.unit_var.get())
            self.state['wheel_diameter_m'] = diameter_m
            self.next_callback()
        except Exception:
            custom_error_popup(self, "Input Error", "Please enter only positive numbers for tire data.")


class DrivetrainStep(ttk.Frame):
    def __init__(self, master, state, next_callback, prev_callback):
        super().__init__(master)
        self.state = state
        self.next_callback = next_callback
        self.prev_callback = prev_callback
        label = ttk.Label(self, text="Step 2: Drivetrain Settings", font=("Segoe UI", 16))
        label.pack(pady=15)
        frame = ttk.Frame(self)
        frame.pack(pady=15)
        ttk.Label(frame, text="Final Drive Ratio:").grid(row=0, column=0, sticky='e')
        self.entry_final_drive = ttk.Entry(frame, width=10)
        self.entry_final_drive.grid(row=0, column=1, padx=10)
        ttk.Label(frame, text="Max Engine RPM:").grid(row=1, column=0, sticky='e')
        self.entry_max_rpm = ttk.Entry(frame, width=10)
        self.entry_max_rpm.grid(row=1, column=1, padx=10)
        ttk.Label(frame, text="Number of Gears (1-24):").grid(row=2, column=0, sticky='e')
        self.entry_num_gears = ttk.Entry(frame, width=10)
        self.entry_num_gears.grid(row=2, column=1, padx=10)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="← Back", command=self.prev_callback).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Next →", command=self.on_next).pack(side='left', padx=5)

    def reset(self):
        self.entry_final_drive.delete(0, 'end')
        self.entry_max_rpm.delete(0, 'end')
        self.entry_num_gears.delete(0, 'end')

    def on_next(self):
        try:
            fd = float(self.entry_final_drive.get())
            rpm = int(self.entry_max_rpm.get())
            gears = int(self.entry_num_gears.get())
            # Validate final drive ratio
            if fd <= 0:
                raise ValueError("Final drive ratio must be a positive number.")
            if gears < 1 or gears > MAX_GEARS:
                raise ValueError("Gears out of range.")
            if rpm < MIN_RPM:
                raise ValueError("Max RPM too low.")
            self.state['final_drive'] = fd
            self.state['max_rpm'] = rpm
            self.state['num_gears'] = gears
            self.next_callback()
        except Exception:
            custom_error_popup(self, "Input Error", f"Please enter valid numbers. Final drive must be positive. Gears: 1-{MAX_GEARS}, RPM ≥ {MIN_RPM}.", width=600, height=300)

class GearRatiosStep(ttk.Frame):
    def __init__(self, master, state, next_callback, prev_callback):
        super().__init__(master)
        self.state = state
        self.next_callback = next_callback
        self.prev_callback = prev_callback
        self.entries = []
        self.label = ttk.Label(self, text="Step 3: Enter Gear Ratios", font=("Segoe UI", 16))
        self.label.pack(pady=15)
        self.frame_gears = ttk.Frame(self)
        self.frame_gears.pack(pady=15)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="← Back", command=self.prev_callback).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Next →", command=self.on_next).pack(side='left', padx=5)

    def tkraise(self, aboveThis=None):
        super().tkraise(aboveThis)
        self.refresh_entries()

    def refresh_entries(self):
        for widget in self.frame_gears.winfo_children():
            widget.destroy()
        self.entries.clear()
        num_gears = self.state.get('num_gears', 0)
        for i in range(num_gears):
            ttk.Label(self.frame_gears, text=f"Gear {i+1} Ratio:").grid(row=i, column=0, sticky='e')
            ent = ttk.Entry(self.frame_gears, width=10)
            ent.grid(row=i, column=1, padx=10, pady=2)
            self.entries.append(ent)

    def reset(self):
        self.entries.clear()
        for widget in self.frame_gears.winfo_children():
            widget.destroy()

    def on_next(self):
        try:
            ratios = []
            for i, ent in enumerate(self.entries):
                val = float(ent.get())
                if val <= 0:
                    raise ValueError("Ratio must be positive.")
                ratios.append(val)
            self.state['gear_ratios'] = ratios
            self.next_callback()
        except Exception:
            custom_error_popup(self, "Input Error", "Please enter a valid positive ratio for every gear.")

class OutputStep(ttk.Frame):
    def __init__(self, master, state, next_callback, prev_callback):
        super().__init__(master)
        self.state = state
        self.next_callback = next_callback
        self.prev_callback = prev_callback
        label = ttk.Label(self, text="Step 4: Output Options", font=("Segoe UI", 16))
        label.pack(pady=15)
        frame = ttk.Frame(self)
        frame.pack(pady=10)
        self.unit_var = tk.StringVar(value="km/h")
        ttk.Label(frame, text="Speed Unit:").grid(row=0, column=0, sticky='e')
        ttk.Radiobutton(frame, text="km/h", variable=self.unit_var, value="km/h").grid(row=0, column=1)
        ttk.Radiobutton(frame, text="mph", variable=self.unit_var, value="mph").grid(row=0, column=2)
        self.display_var = tk.StringVar(value="both")
        ttk.Label(frame, text="Show:").grid(row=1, column=0, sticky='e')
        ttk.Radiobutton(frame, text="Table", variable=self.display_var, value="table").grid(row=1, column=1)
        ttk.Radiobutton(frame, text="Graph", variable=self.display_var, value="graph").grid(row=1, column=2)
        ttk.Radiobutton(frame, text="Both", variable=self.display_var, value="both").grid(row=1, column=3)
        self.save_csv = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, text="Save results as CSV", variable=self.save_csv).pack(pady=5)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="← Back", command=self.prev_callback).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Calculate!", command=self.on_next).pack(side='left', padx=5)

    def on_next(self):
        self.state['unit'] = self.unit_var.get()
        self.state['display'] = self.display_var.get()
        self.state['save_csv'] = self.save_csv.get()
        self.next_callback()

class ResultsStep(ttk.Frame):
    def __init__(self, master, state):
        super().__init__(master)
        self.state = state
        self.label = ttk.Label(self, text="Results", font=("Segoe UI", 16))
        self.label.pack(pady=10)
        self.frame_out = ttk.Frame(self)
        self.frame_out.pack(pady=5, fill='both', expand=True)
        self.table = None
        self.canvas = None
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="New Calculation", command=self.on_new_calc).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Exit", command=self.quit).pack(side='left', padx=10)

    def on_new_calc(self):
        def handle_yes():
            dialog.destroy()
            self.master.reset_all()
            self.master.show_step(0)
        def handle_no():
            dialog.destroy()
            self.master.show_step(0)
        dialog = tk.Toplevel(self)
        dialog.title("New Calculation")
        dialog.geometry("600x250")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        ttk.Label(dialog, text="Do you want to clear all previous inputs?", font=("Segoe UI", 11)).pack(pady=(20,6))
        ttk.Label(dialog, text="Yes: clear all fields and start over.\nNo: keep previous inputs.", font=("Segoe UI", 10)).pack(pady=(0,18))
        btns = ttk.Frame(dialog)
        btns.pack()
        ttk.Button(btns, text="Yes", width=12, command=handle_yes).pack(side='left', padx=16)
        ttk.Button(btns, text="No", width=12, command=handle_no).pack(side='left', padx=16)
        dialog.wait_window()

    def update_results(self):
        for widget in self.frame_out.winfo_children():
            widget.destroy()
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        try:
            wdm = self.state['wheel_diameter_m']
            fd = self.state['final_drive']
            max_rpm = self.state['max_rpm']
            ratios = self.state['gear_ratios']
            unit = self.state['unit']
            display = self.state['display']
            save_csv = self.state['save_csv']
            rpm_values, gear_speeds = gear_speed_table(wdm, fd, max_rpm, ratios, unit)
            headers = ["RPM"] + [f"Gear {i+1}" for i in range(len(ratios))]
            table_data = []
            for idx, rpm in enumerate(rpm_values):
                row = [rpm] + [f"{gear_speeds[g][idx]:.2f}" for g in range(len(ratios))]
                table_data.append(row)
            if save_csv:
                fpath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
                if fpath:
                    export_csv(fpath, headers, table_data)
                    custom_error_popup(self, "Saved", f"Results saved as {fpath}")
            # ---- STYLE (Ubuntu & Windows compatible, mono font for numbers) ----
            style = ttk.Style()
            style.configure("Treeview", rowheight=28, font=("monospace", 10))
            style.configure("Treeview.Heading", font=("monospace", 13, "bold"))
            if display in ["table", "both"]:
                self.table = ttk.Treeview(self.frame_out, columns=headers, show="headings", height=15)
                for col in headers:
                    self.table.heading(col, text=col)
                    self.table.column(col, width=90, minwidth=70, anchor='center')
                for row in table_data:
                    self.table.insert('', 'end', values=row)
                scrollbar_y = ttk.Scrollbar(self.frame_out, orient="vertical", command=self.table.yview)
                scrollbar_x = ttk.Scrollbar(self.frame_out, orient="horizontal", command=self.table.xview)
                self.table.configure(yscroll=scrollbar_y.set, xscroll=scrollbar_x.set)
                self.table.pack(side='left', fill='both', expand=True, padx=5)
                scrollbar_y.pack(side='right', fill='y')
                scrollbar_x.pack(side='bottom', fill='x')
            if display in ["graph", "both"]:
                fig, ax = plt.subplots(figsize=(6, 4))
                for i, speeds in enumerate(gear_speeds):
                    ax.plot(rpm_values, speeds, label=f"Gear {i+1}")
                ax.set_xlabel("Engine RPM")
                ax.set_ylabel(f"Vehicle Speed ({unit})")
                ax.set_title("Speed vs RPM")
                ax.legend()
                ax.grid(True)
                plt.tight_layout()
                self.canvas = FigureCanvasTkAgg(fig, master=self.frame_out)
                self.canvas.draw()
                self.canvas.get_tk_widget().pack(side='left', fill='both', expand=True, padx=10)
        except Exception as e:
            custom_error_popup(self, "Error", f"Calculation failed: {e}")

if __name__ == "__main__":
    app = GearRatioWizard()
    app.mainloop()
