/* Mentora session recorder: 16 kHz mono 16-bit WAV, encoded client-side
 * with the Web Audio API (the host has no ffmpeg). Captures microphone
 * audio, downmixes to mono, and stops automatically at 9:30 with a live
 * timer. No dependencies; wired by the session-room page.
 *
 * Usage:
 *   const rec = new MentoraRecorder({ onTick, onStop, onError });
 *   await rec.start();       // requests mic, begins capture
 *   const blob = await rec.stop();  // 16-bit WAV Blob
 */
(function (global) {
  "use strict";

  var SAMPLE_RATE = 16000;
  var MAX_SECONDS = 570; // 9:30: 570s x 32KB/s ~= 18MB < 32MB API limit

  function encodeWav(chunks, totalSamples) {
    var buffer = new ArrayBuffer(44 + totalSamples * 2);
    var view = new DataView(buffer);
    function writeString(offset, text) {
      for (var i = 0; i < text.length; i++) {
        view.setUint8(offset + i, text.charCodeAt(i));
      }
    }
    writeString(0, "RIFF");
    view.setUint32(4, 36 + totalSamples * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // mono
    view.setUint32(24, SAMPLE_RATE, true);
    view.setUint32(28, SAMPLE_RATE * 2, true); // byte rate
    view.setUint16(32, 2, true); // block align
    view.setUint16(34, 16, true); // bits per sample
    writeString(36, "data");
    view.setUint32(40, totalSamples * 2, true);
    var offset = 44;
    for (var c = 0; c < chunks.length; c++) {
      var data = chunks[c];
      for (var i = 0; i < data.length; i++) {
        var sample = Math.max(-1, Math.min(1, data[i]));
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
        offset += 2;
      }
    }
    return new Blob([buffer], { type: "audio/wav" });
  }

  function MentoraRecorder(callbacks) {
    callbacks = callbacks || {};
    this.onTick = callbacks.onTick || function () {};
    this.onStop = callbacks.onStop || function () {};
    this.onError = callbacks.onError || function () {};
    this.maxSeconds = callbacks.maxSeconds || MAX_SECONDS;
    this.workletUrl = callbacks.workletUrl || "/static/js/recorder-worklet.js";
    this.chunks = [];
    this.totalSamples = 0;
    this.context = null;
    this.stream = null;
    this.timer = null;
    this.startedAt = 0;
    this.recording = false;
  }

  MentoraRecorder.SAMPLE_RATE = SAMPLE_RATE;
  MentoraRecorder.MAX_SECONDS = MAX_SECONDS;

  MentoraRecorder.prototype.elapsed = function () {
    if (!this.startedAt) return 0;
    return (Date.now() - this.startedAt) / 1000;
  };

  MentoraRecorder.prototype.start = function () {
    var self = this;
    if (this.recording) return Promise.resolve();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return Promise.reject(new Error("microphone capture is not supported"));
    }
    var AudioContext = global.AudioContext || global.webkitAudioContext;
    if (!AudioContext) {
      return Promise.reject(new Error("Web Audio is not supported"));
    }
    return navigator.mediaDevices
      .getUserMedia({ audio: { channelCount: 1, echoCancellation: true } })
      .then(function (stream) {
        // 16 kHz context: the browser resamples the hardware rate for us.
        var context = new AudioContext({ sampleRate: SAMPLE_RATE });
        var source = context.createMediaStreamSource(stream);
        return context.audioWorklet
          .addModule(self.workletUrl)
          .then(function () {
            var tap = new AudioWorkletNode(context, "mentora-tap", {
              numberOfInputs: 1,
              numberOfOutputs: 0,
              channelCount: 1,
            });
            tap.port.onmessage = function (event) {
              self.chunks.push(event.data);
              self.totalSamples += event.data.length;
            };
            source.connect(tap);
            self.context = context;
            self.stream = stream;
            self.chunks = [];
            self.totalSamples = 0;
            self.startedAt = Date.now();
            self.recording = true;
            self.timer = global.setInterval(function () {
              var elapsed = self.elapsed();
              self.onTick(elapsed, self.maxSeconds);
              if (elapsed >= self.maxSeconds) {
                self.stop("time limit reached (9:30 maximum)");
              }
            }, 250);
            self.onTick(0, self.maxSeconds);
          })
          .catch(function (err) {
            stream.getTracks().forEach(function (track) { track.stop(); });
            context.close();
            throw err;
          });
      })
      .catch(function (err) {
        self.onError(err);
        throw err;
      });
  };

  MentoraRecorder.prototype.stop = function (reason) {
    var self = this;
    if (!this.recording) return Promise.resolve(null);
    this.recording = false;
    if (this.timer) {
      global.clearInterval(this.timer);
      this.timer = null;
    }
    var blob = encodeWav(this.chunks, this.totalSamples);
    var context = this.context;
    if (this.stream) {
      this.stream.getTracks().forEach(function (track) { track.stop(); });
      this.stream = null;
    }
    function finish() {
      self.context = null;
      self.onStop(blob, reason || "stopped");
      return blob;
    }
    if (context && context.close) {
      return context.close().then(finish, finish);
    }
    return Promise.resolve(finish());
  };

  global.MentoraRecorder = MentoraRecorder;
})(typeof window !== "undefined" ? window : this);
