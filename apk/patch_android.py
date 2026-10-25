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
open(os.path.join(jdir, "AudioRoute.java"), "w").write(r'''package com.shubham.jenny;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioDeviceInfo;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTrack;
import android.os.Build;
import android.util.Base64;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@CapacitorPlugin(name = "AudioRoute")
public class AudioRoute extends Plugin {
    private int oldMode = AudioManager.MODE_NORMAL;
    private boolean oldSpeaker = false;
    private boolean saved = false;
    private AudioTrack track = null;
    private final ExecutorService exec = Executors.newSingleThreadExecutor();

    private AudioManager am() {
        return (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
    }

    @PluginMethod
    public void setEarpiece(PluginCall call) {
        boolean on = call.getBoolean("on", true);
        AudioManager am = am();
        JSObject ret = new JSObject();
        try {
            if (on) {
                if (!saved) { oldMode = am.getMode(); oldSpeaker = am.isSpeakerphoneOn(); saved = true; }
                am.setMode(AudioManager.MODE_IN_COMMUNICATION);
                boolean done = false;
                if (Build.VERSION.SDK_INT >= 31) {
                    List<AudioDeviceInfo> devs = am.getAvailableCommunicationDevices();
                    for (AudioDeviceInfo d : devs) {
                        int t = d.getType();
                        if (t == AudioDeviceInfo.TYPE_BLUETOOTH_SCO || t == AudioDeviceInfo.TYPE_WIRED_HEADSET
                                || t == AudioDeviceInfo.TYPE_WIRED_HEADPHONES || t == AudioDeviceInfo.TYPE_USB_HEADSET) {
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

    @PluginMethod
    public void setSpeaker(PluginCall call) {
        boolean on = call.getBoolean("on", false);
        AudioManager am = am();
        JSObject ret = new JSObject();
        try {
            if (!saved) { oldMode = am.getMode(); oldSpeaker = am.isSpeakerphoneOn(); saved = true; }
            am.setMode(AudioManager.MODE_IN_COMMUNICATION);
            boolean done = false;
            String name = "";
            if (Build.VERSION.SDK_INT >= 31) {
                List<AudioDeviceInfo> devs = am.getAvailableCommunicationDevices();
                if (on) {
                    for (AudioDeviceInfo d : devs) {
                        if (d.getType() == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER) {
                            done = am.setCommunicationDevice(d);
                            name = "speaker";
                            break;
                        }
                    }
                } else {
                    for (AudioDeviceInfo d : devs) {
                        int t = d.getType();
                        if (t == AudioDeviceInfo.TYPE_BLUETOOTH_SCO || t == AudioDeviceInfo.TYPE_WIRED_HEADSET
                                || t == AudioDeviceInfo.TYPE_WIRED_HEADPHONES || t == AudioDeviceInfo.TYPE_USB_HEADSET) {
                            done = am.setCommunicationDevice(d);
                            name = "headset";
                            if (done) break;
                        }
                    }
                    if (!done) {
                        for (AudioDeviceInfo d : devs) {
                            if (d.getType() == AudioDeviceInfo.TYPE_BUILTIN_EARPIECE) {
                                done = am.setCommunicationDevice(d);
                                name = "earpiece";
                                break;
                            }
                        }
                    }
                }
            }
            if (!done) { am.setSpeakerphoneOn(on); name = on ? "speaker" : "earpiece"; }
            ret.put("ok", true);
            ret.put("route", name);
        } catch (Exception e) {
            ret.put("ok", false);
            ret.put("error", String.valueOf(e.getMessage()));
        }
        call.resolve(ret);
    }

    @PluginMethod
    public void startPlayer(PluginCall call) {
        JSObject ret = new JSObject();
        try {
            stopTrack();
            int rate = 24000;
            int min = AudioTrack.getMinBufferSize(rate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT);
            AudioAttributes attrs = new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build();
            AudioFormat fmt = new AudioFormat.Builder()
                    .setSampleRate(rate)
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build();
            track = new AudioTrack(attrs, fmt, Math.max(min * 4, rate * 2), AudioTrack.MODE_STREAM, AudioManager.AUDIO_SESSION_ID_GENERATE);
            track.play();
            ret.put("ok", true);
        } catch (Exception e) {
            track = null;
            ret.put("ok", false);
            ret.put("error", String.valueOf(e.getMessage()));
        }
        call.resolve(ret);
    }

    @PluginMethod
    public void write(PluginCall call) {
        final String data = call.getString("data", "");
        final AudioTrack t = track;
        if (t != null && data != null && data.length() > 0) {
            exec.execute(new Runnable() {
                @Override
                public void run() {
                    try {
                        byte[] b = Base64.decode(data, Base64.DEFAULT);
                        t.write(b, 0, b.length);
                    } catch (Exception e) { }
                }
            });
        }
        call.resolve();
    }

    @PluginMethod
    public void flush(PluginCall call) {
        final AudioTrack t = track;
        if (t != null) {
            try {
                t.pause();
                t.flush();
                t.play();
            } catch (Exception e) { }
        }
        call.resolve();
    }

    @PluginMethod
    public void stopPlayer(PluginCall call) {
        stopTrack();
        call.resolve();
    }

    private void stopTrack() {
        AudioTrack t = track;
        track = null;
        if (t != null) {
            try { t.stop(); } catch (Exception e) { }
            try { t.release(); } catch (Exception e) { }
        }
    }
}
''')
open(os.path.join(jdir, "MainActivity.java"), "w").write('''package com.shubham.jenny;

import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AudioRoute.class);
        super.onCreate(savedInstanceState);
        try {
            WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
            getWindow().setStatusBarColor(Color.parseColor("#150f1d"));
            getWindow().setNavigationBarColor(Color.parseColor("#150f1d"));
            View content = findViewById(android.R.id.content);
            content.setBackgroundColor(Color.parseColor("#150f1d"));
            ViewCompat.setOnApplyWindowInsetsListener(content, (v, insets) -> {
                Insets b = insets.getInsets(WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.ime());
                v.setPadding(b.left, b.top, b.right, b.bottom);
                return WindowInsetsCompat.CONSUMED;
            });
            ViewCompat.requestApplyInsets(content);
        } catch (Exception e) { }
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
gp = os.path.join("android", "app", "build.gradle")
g = open(gp).read()
if "signingConfigs" not in g:
    sc = """    signingConfigs {
        debug {
            storeFile file("${rootDir}/../jenny.keystore")
            storePassword "jennyapp"
            keyAlias "jenny"
            keyPassword "jennyapp"
        }
    }
    buildTypes {"""
    g = g.replace("    buildTypes {", sc, 1)
    open(gp, "w").write(g)
print("patched")
