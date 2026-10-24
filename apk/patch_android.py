import os, re, sys
from PIL import Image

root = os.path.join("android", "app", "src", "main")
man = os.path.join(root, "AndroidManifest.xml")
x = open(man).read()
perms = ["android.permission.INTERNET", "android.permission.RECORD_AUDIO",
         "android.permission.MODIFY_AUDIO_SETTINGS", "android.permission.WAKE_LOCK",
         "android.permission.VIBRATE"]
add = "".join('    <uses-permission android:name="%s" />\n' % p for p in perms if p not in x)
x = x.replace("</manifest>", add + "</manifest>")
open(man, "w").write(x)

# package dir
pkg = "com/shubham/jenny"
jdir = os.path.join(root, "java", *pkg.split("/"))
os.makedirs(jdir, exist_ok=True)
open(os.path.join(jdir, "AudioRoute.java"), "w").write('''package com.shubham.jenny;

import android.content.Context;
import android.media.AudioDeviceInfo;
import android.media.AudioManager;
import android.os.Build;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.List;

@CapacitorPlugin(name = "AudioRoute")
public class AudioRoute extends Plugin {
    private int oldMode = AudioManager.MODE_NORMAL;
    private boolean oldSpeaker = false;
    private boolean saved = false;

    @PluginMethod
    public void setEarpiece(PluginCall call) {
        boolean on = call.getBoolean("on", true);
        AudioManager am = (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
        JSObject ret = new JSObject();
        try {
            if (on) {
                if (!saved) { oldMode = am.getMode(); oldSpeaker = am.isSpeakerphoneOn(); saved = true; }
                am.setMode(AudioManager.MODE_IN_COMMUNICATION);
                boolean done = false;
                if (Build.VERSION.SDK_INT >= 31) {
                    List<AudioDeviceInfo> devs = am.getAvailableCommunicationDevices();
                    for (AudioDeviceInfo d : devs) {
                        if (d.getType() == AudioDeviceInfo.TYPE_BLUETOOTH_SCO
                                || d.getType() == AudioDeviceInfo.TYPE_WIRED_HEADSET
                                || d.getType() == AudioDeviceInfo.TYPE_WIRED_HEADPHONES
                                || d.getType() == AudioDeviceInfo.TYPE_USB_HEADSET) {
                            done = am.setCommunicationDevice(d);
                            if (done) break;
                        }
                    }
                    if (!done) {
                        for (AudioDeviceInfo d : devs) {
                            if (d.getType() == AudioDeviceInfo.TYPE_BUILTIN_EARPIECE) {
                                done = am.setCommunicationDevice(d);
                                break;
                            }
                        }
                    }
                }
                if (!done) am.setSpeakerphoneOn(false);
            } else {
                if (Build.VERSION.SDK_INT >= 31) am.clearCommunicationDevice();
                am.setSpeakerphoneOn(oldSpeaker);
                am.setMode(saved ? oldMode : AudioManager.MODE_NORMAL);
                saved = false;
            }
            ret.put("ok", true);
        } catch (Exception e) {
            ret.put("ok", false);
            ret.put("error", String.valueOf(e.getMessage()));
        }
        call.resolve(ret);
    }
}
''')
open(os.path.join(jdir, "MainActivity.java"), "w").write('''package com.shubham.jenny;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AudioRoute.class);
        super.onCreate(savedInstanceState);
    }
}
''')
# icons
src = Image.open(os.path.join("..", "icon-512.png")).convert("RGBA")
res = os.path.join(root, "res")
anydpi = os.path.join(res, "mipmap-anydpi-v26")
if os.path.isdir(anydpi):
    import shutil; shutil.rmtree(anydpi)
sizes = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
for k, px in sizes.items():
    d = os.path.join(res, "mipmap-" + k)
    os.makedirs(d, exist_ok=True)
    im = src.resize((px, px), Image.LANCZOS)
    im.save(os.path.join(d, "ic_launcher.png"))
    im.save(os.path.join(d, "ic_launcher_round.png"))
    for f in ("ic_launcher_foreground.png",):
        p = os.path.join(d, f)
        if os.path.exists(p): os.remove(p)
    for f in os.listdir(d):
        if f.endswith(".webp"): os.remove(os.path.join(d, f))
print("patched")
