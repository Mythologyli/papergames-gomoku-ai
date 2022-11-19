import logging
import subprocess
from pathlib import Path


class PiskvorkManager:
    def __init__(self, logger: logging.Logger, pbrain_path: Path, timeout_turn: float):
        self.logger = logger

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            self.proc = subprocess.Popen(
                str(pbrain_path),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                startupinfo=startupinfo
            )
        except FileNotFoundError:
            self.logger.error(f"Piskvork brain not found in {str(pbrain_path)}")
            self.proc = None
            return

        if timeout_turn != 0:
            # Set timeout for a turn
            self._write_input(f"INFO timeout_turn {int(timeout_turn * 1000)}")

        # Start a 15x15 game
        self._write_input('START 15')

        # Check if piskvork brain started successfully
        for i in range(5):
            output_str = self.proc.stdout.readline().decode('utf-8')
            self.logger.debug(f"Brain output: {output_str.strip()}")
            if "OK" in output_str:
                self.logger.info('Piskvork brain OK!')
                return

        self.logger.error(f"Fail to start piskvork brain in {str(pbrain_path)}.")
        self.proc = None

    def _write_input(self, input_str: str) -> None:
        self.proc.stdin.write((input_str + '\r\n').encode('utf-8'))
        self.proc.stdin.flush()
        self.logger.debug(f"Brain input: {input_str}")

    def _read_move_output(self) -> tuple[int, int]:
        while True:
            output_str = self.proc.stdout.readline().decode('utf-8')
            self.logger.debug(f"Brain output: {output_str.strip()}")
            output_str_split = output_str.strip().split(',')
            if len(output_str_split) == 2 and output_str_split[0].isdigit() and output_str_split[1].isdigit():
                return int(output_str_split[0]), int(output_str_split[1])

    def begin(self) -> tuple[int, int]:
        self._write_input('BEGIN')

        return self._read_move_output()

    def get_move(self, x: int, y: int) -> tuple[int, int]:
        self._write_input(f'TURN {x},{y}')

        return self._read_move_output()

    def kill(self):
        self.proc.kill()
