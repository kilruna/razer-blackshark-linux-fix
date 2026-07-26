# Razer BlackShark V2 Pro 2023 Linux initialization workaround

This repository contains an interactive workaround for the Razer BlackShark
V2 Pro 2023 USB dongle. It supports **only USB ID `1532:0555`**.

## Symptoms

On affected systems, the headset dongle may appear but audio output, microphone,
or media/volume controls do not all work after it is connected. The workaround
was successfully tested on Bazzite KDE with the Razer BlackShark V2 Pro 2023
2.4 GHz USB dongle (`1532:0555`).

The available evidence suggests an initialization-order issue between the
dongle HID/firmware and `snd_usb_audio`. The exact upstream cause has not been
proven. Related tracking and discussion:
[Bazzite issue #5297](https://github.com/ublue-os/bazzite/issues/5297).

## How it works

The helper preserves the tested interactive sequence:

1. Create a temporary runtime-only block for `snd_usb_audio`.
2. Stop PipeWire and WirePlumber for the desktop user who invoked `sudo`.
3. Ask that user to physically unplug the dongle.
4. Unload `snd_usb_audio`.
5. Ask the user to reconnect exactly USB device `1532:0555`.
6. Wait for a real `KEY_VOLUMEUP` or `KEY_VOLUMEDOWN` input event.
7. Remove the temporary module block and load `snd_usb_audio`.
8. Verify that all three dongle audio interfaces bind to the driver.
9. Restart PipeWire and WirePlumber.

The helper does not install udev rules, modprobe overrides, or WirePlumber
configuration. It does not modify existing audio configuration.

## Installation and use

From this repository:

```bash
sudo ./install.sh
sudo /usr/local/sbin/razer-blackshark-fix
```

Run the helper with `sudo` from the affected user's active graphical desktop
session. Follow the unplug, reconnect, and volume-rocker prompts. To run without
installing:

```bash
sudo ./razer-blackshark-fix
```

## Removal

```bash
sudo ./uninstall.sh
```

Removal deletes only `/usr/local/sbin/razer-blackshark-fix`. There are no
persistent configuration files to remove.

## Safety warnings

- Only the `1532:0555` dongle is detected and verified.
- The helper temporarily interrupts audio for the invoking desktop user.
- It never forcibly unbinds USB audio interfaces. If another USB audio device
  prevents `snd_usb_audio` from unloading, the helper aborts and explains why.
- Do not remove the temporary file in `/run/modprobe.d` while the helper is
  running.
- Disconnect other USB audio equipment only when it is safe to do so.
- Errors, signals, and timeouts trigger cleanup that removes the temporary block,
  reloads `snd_usb_audio`, and restarts the user's audio services.

## Troubleshooting

**`snd_usb_audio could not be unloaded`**

Another USB audio device is probably using the shared kernel module. Safely
disconnect that device and retry. The helper intentionally does not unbind it.

**The desktop user session bus is unavailable**

Run the command through `sudo` in a terminal inside the active KDE session, not
from a root shell, SSH session, or system service.

**The dongle or HID interface times out**

Confirm with `lsusb` that the device reports `1532:0555`, try another direct USB
port, and run the helper again. Hubs can change reconnect timing.

**Audio services do not return after an unexpected system-level failure**

As the normal desktop user, run:

```bash
systemctl --user restart pipewire pipewire-pulse wireplumber
```

## Manual `evtest` verification

Install `evtest` using your distribution's package manager, then identify the
Razer Consumer Control event device:

```bash
ls -l /dev/input/by-id/*Razer_BlackShark*event-if03
sudo evtest /dev/input/by-id/usb-1532_Razer_BlackShark_V2_Pro_2.4_*-event-if03
```

Move the volume rocker. A working HID path reports `KEY_VOLUMEUP` (code 115) or
`KEY_VOLUMEDOWN` (code 114). Exit with Ctrl+C. Check that the wildcard resolves
to a single device before passing it to `evtest`.

## Known limitations

- No hardware other than the Razer BlackShark V2 Pro 2023 dongle with USB ID
  `1532:0555` is supported.
- The process is deliberately interactive and cannot run unattended.
- It briefly stops the invoking user's PipeWire/WirePlumber session.
- Other USB audio devices using `snd_usb_audio` must be disconnected before the
  module can be unloaded.
- The workaround addresses observed initialization behavior; it is not a proven
  upstream kernel or firmware fix.
