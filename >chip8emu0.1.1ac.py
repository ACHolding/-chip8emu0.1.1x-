import tkinter as tk
from tkinter import filedialog, messagebox
import random
import time

# ============================================================
# CHIP-8 Emulator - Tkinter, single file
# ============================================================

WINDOW_W = 600
WINDOW_H = 400
SCALE = 8
SCREEN_W = 64
SCREEN_H = 32

FONTSET = [
    0xF0,0x90,0x90,0x90,0xF0, 0x20,0x60,0x20,0x20,0x70,
    0xF0,0x10,0xF0,0x80,0xF0, 0xF0,0x10,0xF0,0x10,0xF0,
    0x90,0x90,0xF0,0x10,0x10, 0xF0,0x80,0xF0,0x10,0xF0,
    0xF0,0x80,0xF0,0x90,0xF0, 0xF0,0x10,0x20,0x40,0x40,
    0xF0,0x90,0xF0,0x90,0xF0, 0xF0,0x90,0xF0,0x10,0xF0,
    0xF0,0x90,0xF0,0x90,0x90, 0xE0,0x90,0xE0,0x90,0xE0,
    0xF0,0x80,0x80,0x80,0xF0, 0xE0,0x90,0x90,0x90,0xE0,
    0xF0,0x80,0xF0,0x80,0xF0, 0xF0,0x80,0xF0,0x80,0x80
]

KEYMAP = {
    "1":0x1, "2":0x2, "3":0x3, "4":0xC,
    "q":0x4, "w":0x5, "e":0x6, "r":0xD,
    "a":0x7, "s":0x8, "d":0x9, "f":0xE,
    "z":0xA, "x":0x0, "c":0xB, "v":0xF
}

class Chip8:
    def __init__(self):
        self.reset()

    def reset(self):
        self.memory = [0] * 4096
        self.V = [0] * 16
        self.I = 0
        self.pc = 0x200
        self.stack = []
        self.delay = 0
        self.sound = 0
        self.keys = [False] * 16
        self.display = [0] * (SCREEN_W * SCREEN_H)
        self.waiting_key = None
        self.draw_flag = True
        self.memory[0x50:0x50+len(FONTSET)] = FONTSET[:]

    def load_rom(self, data):
        self.reset()
        if len(data) > 4096 - 0x200:
            raise ValueError("ROM is too large for CHIP-8 memory.")
        self.memory[0x200:0x200+len(data)] = data

    def cycle(self):
        if self.waiting_key is not None:
            return

        if self.pc + 1 >= 4096:
            return

        op = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc = (self.pc + 2) & 0xFFF

        nnn = op & 0x0FFF
        nn = op & 0x00FF
        n = op & 0x000F
        x = (op >> 8) & 0xF
        y = (op >> 4) & 0xF

        if op == 0x00E0:
            self.display = [0] * (SCREEN_W * SCREEN_H)
            self.draw_flag = True

        elif op == 0x00EE:
            if self.stack:
                self.pc = self.stack.pop()

        elif op & 0xF000 == 0x1000:
            self.pc = nnn

        elif op & 0xF000 == 0x2000:
            if len(self.stack) < 16:
                self.stack.append(self.pc)
                self.pc = nnn

        elif op & 0xF000 == 0x3000:
            if self.V[x] == nn:
                self.pc += 2

        elif op & 0xF000 == 0x4000:
            if self.V[x] != nn:
                self.pc += 2

        elif op & 0xF00F == 0x5000:
            if self.V[x] == self.V[y]:
                self.pc += 2

        elif op & 0xF000 == 0x6000:
            self.V[x] = nn

        elif op & 0xF000 == 0x7000:
            self.V[x] = (self.V[x] + nn) & 0xFF

        elif op & 0xF00F == 0x8000:
            self.V[x] = self.V[y]

        elif op & 0xF00F == 0x8001:
            self.V[x] |= self.V[y]

        elif op & 0xF00F == 0x8002:
            self.V[x] &= self.V[y]

        elif op & 0xF00F == 0x8003:
            self.V[x] ^= self.V[y]

        elif op & 0xF00F == 0x8004:
            total = self.V[x] + self.V[y]
            self.V[0xF] = 1 if total > 255 else 0
            self.V[x] = total & 0xFF

        elif op & 0xF00F == 0x8005:
            self.V[0xF] = 1 if self.V[x] >= self.V[y] else 0
            self.V[x] = (self.V[x] - self.V[y]) & 0xFF

        elif op & 0xF00F == 0x8006:
            self.V[0xF] = self.V[x] & 1
            self.V[x] >>= 1

        elif op & 0xF00F == 0x8007:
            self.V[0xF] = 1 if self.V[y] >= self.V[x] else 0
            self.V[x] = (self.V[y] - self.V[x]) & 0xFF

        elif op & 0xF00F == 0x800E:
            self.V[0xF] = (self.V[x] >> 7) & 1
            self.V[x] = (self.V[x] << 1) & 0xFF

        elif op & 0xF00F == 0x9000:
            if self.V[x] != self.V[y]:
                self.pc += 2

        elif op & 0xF000 == 0xA000:
            self.I = nnn

        elif op & 0xF000 == 0xB000:
            self.pc = (nnn + self.V[0]) & 0xFFF

        elif op & 0xF000 == 0xC000:
            self.V[x] = random.randint(0, 255) & nn

        elif op & 0xF000 == 0xD000:
            vx = self.V[x] % SCREEN_W
            vy = self.V[y] % SCREEN_H
            self.V[0xF] = 0

            for row in range(n):
                if self.I + row >= 4096:
                    break
                sprite = self.memory[self.I + row]
                for bit in range(8):
                    if sprite & (0x80 >> bit):
                        px = (vx + bit) % SCREEN_W
                        py = (vy + row) % SCREEN_H
                        pos = py * SCREEN_W + px
                        if self.display[pos]:
                            self.V[0xF] = 1
                        self.display[pos] ^= 1

            self.draw_flag = True

        elif op & 0xF0FF == 0xE09E:
            if self.keys[self.V[x] & 0xF]:
                self.pc += 2

        elif op & 0xF0FF == 0xE0A1:
            if not self.keys[self.V[x] & 0xF]:
                self.pc += 2

        elif op & 0xF0FF == 0xF007:
            self.V[x] = self.delay

        elif op & 0xF0FF == 0xF00A:
            self.waiting_key = x

        elif op & 0xF0FF == 0xF015:
            self.delay = self.V[x]

        elif op & 0xF0FF == 0xF018:
            self.sound = self.V[x]

        elif op & 0xF0FF == 0xF01E:
            self.I = (self.I + self.V[x]) & 0xFFF

        elif op & 0xF0FF == 0xF029:
            self.I = 0x50 + (self.V[x] & 0xF) * 5

        elif op & 0xF0FF == 0xF033:
            value = self.V[x]
            self.memory[self.I] = value // 100
            self.memory[self.I + 1] = (value // 10) % 10
            self.memory[self.I + 2] = value % 10

        elif op & 0xF0FF == 0xF055:
            for i in range(x + 1):
                self.memory[self.I + i] = self.V[i]

        elif op & 0xF0FF == 0xF065:
            for i in range(x + 1):
                self.V[i] = self.memory[self.I + i]

    def tick_timers(self):
        if self.delay > 0:
            self.delay -= 1
        if self.sound > 0:
            self.sound -= 1


class App:
    def __init__(self, root):
        self.root = root
        self.vm = Chip8()
        self.loaded = False
        self.running = False
        self.last_timer = time.perf_counter()
        self.audio_active = False

        root.title("CHIP-8 Emulator")
        root.resizable(False, False)

        root.update_idletasks()
        px = (root.winfo_screenwidth() - WINDOW_W) // 2
        py = (root.winfo_screenheight() - WINDOW_H) // 2
        root.geometry(f"{WINDOW_W}x{WINDOW_H}+{px}+{py}")

        # Blank menu bar: only the standard menu labels, no "No game" text.
        bar = tk.Menu(root)

        file_menu = tk.Menu(bar, tearoff=False)
        file_menu.add_command(label="Open ROM...", command=self.open_rom)
        file_menu.add_command(label="Close ROM", command=self.close_rom)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.destroy)
        bar.add_cascade(label="File", menu=file_menu)

        emu_menu = tk.Menu(bar, tearoff=False)
        emu_menu.add_command(label="Run / Pause", command=self.toggle_run)
        emu_menu.add_command(label="Reset", command=self.reset)
        bar.add_cascade(label="Emulation", menu=emu_menu)

        help_menu = tk.Menu(bar, tearoff=False)
        help_menu.add_command(
            label="About",
            command=lambda: messagebox.showinfo(
                "CHIP-8 Emulator",
                "CHIP-8 Emulator\nTkinter 600x400"
            )
        )
        bar.add_cascade(label="Help", menu=help_menu)
        root.config(menu=bar)

        self.canvas = tk.Canvas(
            root,
            width=WINDOW_W,
            height=WINDOW_H,
            bg="#0000aa",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        root.bind("<KeyPress>", self.key_down)
        root.bind("<KeyRelease>", self.key_up)
        root.bind("<Control-o>", lambda e: self.open_rom())
        root.bind("<space>", lambda e: self.toggle_run())

        self.render()
        self.loop()

    def open_rom(self):
        path = filedialog.askopenfilename(
            title="Open CHIP-8 ROM",
            filetypes=[
                ("CHIP-8 ROMs", "*.ch8 *.c8 *.rom"),
                ("All files", "*.*")
            ]
        )
        if not path:
            return

        try:
            with open(path, "rb") as f:
                data = list(f.read())
            self.vm.load_rom(data)
            self.loaded = True
            self.running = True
            self.root.title("CHIP-8 Emulator")
            self.render()
        except Exception as exc:
            messagebox.showerror("CHIP-8 Emulator", str(exc))

    def close_rom(self):
        self.vm.reset()
        self.loaded = False
        self.running = False
        self.root.title("CHIP-8 Emulator")
        self.render()

    def reset(self):
        if not self.loaded:
            self.vm.reset()
            self.render()
            return
        self.open_rom()

    def toggle_run(self):
        if self.loaded:
            self.running = not self.running

    def key_down(self, event):
        key = event.keysym.lower()
        if key in KEYMAP:
            value = KEYMAP[key]
            self.vm.keys[value] = True
            if self.vm.waiting_key is not None:
                self.vm.V[self.vm.waiting_key] = value
                self.vm.waiting_key = None

    def key_up(self, event):
        key = event.keysym.lower()
        if key in KEYMAP:
            self.vm.keys[KEYMAP[key]] = False

    def render(self):
        self.canvas.delete("all")

        # Full blue CHIP-8 display, matching the reference's visual style.
        self.canvas.configure(bg="#0000aa")

        pixel_w = WINDOW_W / SCREEN_W
        pixel_h = WINDOW_H / SCREEN_H

        for y in range(SCREEN_H):
            for x in range(SCREEN_W):
                if self.vm.display[y * SCREEN_W + x]:
                    x1 = int(x * pixel_w)
                    y1 = int(y * pixel_h)
                    x2 = int((x + 1) * pixel_w + 1)
                    y2 = int((y + 1) * pixel_h + 1)
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2,
                        fill="#ddffff",
                        outline=""
                    )

        self.vm.draw_flag = False

    def audio_tick(self):
        # FILES_OFF audio: no WAV/MP3/assets. Uses Tk's built-in system bell
        # while CHIP-8 sound_timer is active.
        active = self.running and self.loaded and self.vm.sound > 0
        if active and not self.audio_active:
            self.audio_active = True
            self.root.bell()
        elif not active:
            self.audio_active = False

    def loop(self):
        now = time.perf_counter()

        if self.running and self.loaded:
            # Roughly 700 CHIP-8 instructions/second at a 60 Hz GUI tick.
            for _ in range(12):
                self.vm.cycle()

            if now - self.last_timer >= 1 / 60:
                self.vm.tick_timers()
                self.last_timer = now

            if self.vm.draw_flag:
                self.render()

            self.audio_tick()
        else:
            self.audio_active = False

        self.root.after(16, self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
