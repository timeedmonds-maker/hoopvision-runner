import EaseLive from '@ease-live/ease-live-bridge-web';
let client;
window.ephemeralFeed = {
  initialize: ({accountId,programId}) => new Promise(resolve => {
    let settled = false;
    const done = value => {if (!settled) {settled = true; resolve(value);}};
    try {
      client = new EaseLive({
        accountId, programId, env:'prod', viewContainer:'#overlay',
        playerPlugin: bridge => {bridge.emit('player.ready', {}); return {};}
      });
      client.on('app.ready', () => done('ready'));
      for (const name of ['view.error','app.error','easelive.error']) {
        client.on(name, () => done('error'));
      }
      client.init();
      setTimeout(() => done('timeout'), 16000);
    } catch (_) {done('error');}
  }),
  seek: ms => {
    if (!client || !Number.isSafeInteger(ms)) return false;
    client.emit('player.state', {state:'playing'});
    client.emit('player.time', {timecode:ms});
    return true;
  },
  shutdown: () => {try {client?.destroy();} catch (_) {}}
};
