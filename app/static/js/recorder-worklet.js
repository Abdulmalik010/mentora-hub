/* PCM tap for the Mentora session recorder. Receives mono Float32 frames
 * from the worklet and forwards them to the main thread for WAV encoding. */
class MentoraTapProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel && channel.length) {
      this.port.postMessage(channel.slice(0));
    }
    return true;
  }
}

registerProcessor("mentora-tap", MentoraTapProcessor);
