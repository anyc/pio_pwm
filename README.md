PIO-PWM
=======

PIO-PWM provides a class to output PWM (pulse-width modulation) using the
Raspberry Pico's PIO (Programmable I/O) unit with an interface similar to
MicroPython's generic machine.PWM class.

While the Pico has several hardware PWM generators, one cannot freely assign
them to individual pins [[1][1], [2][2]].

Example
-------

```
from pio_pwm import PIOPWM

pwm = PIOPWM(Pin(12), freq=38_000)
pwm.duty_u16(6500)
time.sleep(1)
pwm.deinit()
```

Description
-----------

```
class PIOPWM(pin, freq=None, duty_u16=None, duty_ns=None, invert=False, sm_id=None, cycle_length=None)
```

The PIOPWM interface is modeled after MicroPython's PWM interface [[3][3]]. The
PIOPWM class additionally accepts the `sm_id` parameter to manually select a
free PIO state machine and the `cycle_length` parameter which defaults to 65536.

Prior work
----------

The PIO code is based on previous work from:
 * https://github.com/raspberrypi/pico-micropython-examples/blob/master/pio/pio_pwm.py
 * https://hackspace.raspberrypi.com/articles/flashing-lights-with-micropython-and-programmable-i-o-part-2

[1]: https://docs.micropython.org/en/latest/rp2/quickref.html#pwm-pulse-width-modulation
[2]: https://forums.raspberrypi.com/viewtopic.php?t=351145
[3]: https://docs.micropython.org/en/latest/library/machine.PWM.html
