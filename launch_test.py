import sys; sys.path.insert(0, ".")
print("Starting...", flush=True)
from akcalc.ui.app import App
print("App imported", flush=True)
app = App()
print("App created", flush=True)
app.after(3000, app.destroy)
app.mainloop()
print("Done", flush=True)
