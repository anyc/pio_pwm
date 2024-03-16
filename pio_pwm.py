#
# PIO-PWM
# -------
#
# PIO-PWM provides a class to output PWM (pulse-width modulation) using the
# Raspberry Pico's PIO (Programmable I/O) unit with an interface similar to
# MicroPython's generic machine.PWM class.
#
# While the Pico has several hardware PWM generators, one cannot freely assign
# them to individual pins [1, 2].
#
# [1] https://docs.micropython.org/en/latest/rp2/quickref.html#pwm-pulse-width-modulation
# [2] https://forums.raspberrypi.com/viewtopic.php?t=351145
#
#
# The PIO code is based on previous work from:
#   https://github.com/raspberrypi/pico-micropython-examples/blob/master/pio/pio_pwm.py
#   https://hackspace.raspberrypi.com/articles/flashing-lights-with-micropython-and-programmable-i-o-part-2
#
# Author: Mario Kicherer <dev@kicherer.org>
#

from machine import Pin
from machine import freq as machine_freq
from time import sleep
from rp2 import PIO, StateMachine, asm_pio

# used to find a free StateMachine automatically
used_sms = [False]*8

@asm_pio(sideset_init=PIO.OUT_LOW)
def pwm_asm():
	pull(noblock).side(0)
	mov(x, osr)
	mov(y, isr)
	label("pwm_loop")
	jmp(x_not_y, "skip")
	nop()        .side(1)
	label("skip")
	jmp(y_dec, "pwm_loop")

@asm_pio(sideset_init=PIO.OUT_HIGH)
def pwm_asm_inv():
	pull(noblock).side(1)
	mov(x, osr)
	mov(y, isr)
	label("pwm_loop")
	jmp(x_not_y, "skip")
	nop()        .side(0)
	label("skip")
	jmp(y_dec, "pwm_loop")

class PIOPWM:
	def __init__(self, pin, freq=None, duty_u16=None, duty_ns=None, invert=False, sm_id=None, cycle_length=None):
		self._pin = pin
		self._freq = freq
		self._duty_u16 = duty_u16
		self._duty_ns = duty_ns
		self._invert = invert
		self._cycle_length_user = cycle_length
		
		self._sm_id = sm_id
		if sm_id is None:
			for i in range(len(used_sms)):
				if not used_sms[i]:
					self._sm_id = i
					break
		if self._sm_id is None:
			raise Exception("no free state machine found")
		
		used_sms[self._sm_id] = True
		
		if self._freq:
			self.freq(self._freq, self._cycle_length_user)
		if self._duty_u16:
			self.duty_u16(self._duty_u16)
		if self._duty_ns:
			self.duty_ns(self._duty_ns)
	
	def __del__(self):
		used_sms[self._sm_id] = False
	
	def freq(self, freq, cycle_length=None):
		if self._invert:
			pio_code = pwm_asm_inv
		else:
			pio_code = pwm_asm
		
		if cycle_length is None:
			if self._cycle_length_user:
				cycle_length = self._cycle_length_user
			else:
				cycle_length = (1 << 16) - 1
		
		# From the requested PWM frequency and cycle length we calculate the
		# necessary PIO frequency and maximum cycle length. If the requested
		# cycle length is not possible, we work with the maximum length and
		# adjust the user values.
		self._cycle_length_user = cycle_length
		if freq * self._cycle_length_user < machine_freq()/2:
			self._freq = int(freq * self._cycle_length_user)
			self._cycle_length = self._cycle_length_user
		else:
			self._freq = int(machine_freq()/2)
			self._cycle_length = int(machine_freq()/2 / freq)
		
		# If the requested freqency is below the minimum for a PIO, we also
		# adjust the values transparently.
		if self._freq < 2030:
			self._sm_freq = 2030
			self._freq_factor = self._sm_freq / self._freq
		else:
			self._sm_freq = self._freq
			self._freq_factor = 1
		
		self._sm = StateMachine(self._sm_id, pio_code, freq=2 * self._sm_freq, sideset_base=self._pin)
		
		self._sm_mode = None
	
	def duty_u16(self, duty_u16):
		self._duty_u16 = int(duty_u16 * self._freq_factor)
		
		if self._sm_mode and self._sm_mode != "u16":
			self._sm.active(0)
			self._sm_mode = None
		
		if self._sm_mode is None:
			self._sm.restart()
			self._sm.put(self._cycle_length)
			self._sm.exec("pull()")
			self._sm.exec("mov(isr, osr)")
			self._sm.active(1)
			self._sm_mode = "u16"
		
		if self._cycle_length != self._cycle_length_user:
			self._duty_u16 = int(self._duty_u16 / self._cycle_length_user * self._cycle_length)
		self.start_pwm(self._duty_u16)
	
	def duty_ns(self, duty_ns):
		self._duty_ns = duty_ns
		
		if self._sm_mode and self._sm_mode != "u16":
			self._sm.active(0)
			self._sm_mode = None
		
		if self._sm_mode is None:
			self._sm.restart()
			self._sm.put(self._cycle_length)
			self._sm.exec("pull()")
			self._sm.exec("mov(isr, osr)")
			self._sm.active(1)
			self._sm_mode = "u16"
		
		duty_cycles = int(duty_ns * self._freq / 1_000_000_000 * self._freq_factor)
		
		self.start_pwm(duty_cycles)
	
	def deinit(self):
		self._sm.active(0)
		self._sm_mode = None
	
	def start_pwm(self, duty_cycles):
		# Minimum value is -1 (completely turn off), 0 actually still produces narrow pulse
		duty_cycles = max(duty_cycles, -1)
		if duty_cycles == 0:
			duty_cycles = -1
		duty_cycles = min(duty_cycles, self._cycle_length-1)
		
		self._sm.put(duty_cycles)

if __name__ == "__main__":
	if True:
		pwm = PIOPWM(Pin(12), freq=38_000)
		pwm.duty_u16(6500)
		
		while True:
			for i in range(256):
				pwm.duty_u16(i ** 2)
				sleep(0.01)
	else:
		# for comparison
		from machine import PWM
		pwm = PWM(Pin(12), freq=38_000)
		pwm.duty_u16(6500)
