const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app.js', 'utf8').split("fetch('data/campionato.json')")[0];
const R = 'POLISPORTIVA REBA', B = 'POLISPORTIVA REBA BIANCO';
function setup(teams, games) {
  const context = vm.createContext({console, Date, Math});
  vm.runInContext(source, context);
  context.fixture = {squadre:{D:teams}, partite:games};
  vm.runInContext('db = fixture', context);
  return expression => JSON.parse(JSON.stringify(vm.runInContext(expression, context)));
}
const game = (id, casa, trasferta, risultato) => ({id, casa, trasferta, risultato, girone:'D', data:'08/11/2026', ora:'10:00'});
test('top two REBA remain distinct; excluded slot does not promote third', () => {
  const run = setup([R,B,'Third'], [game(1,R,B,[60,40]),game(2,R,'Third',[60,40]),game(3,B,'Third',[60,40])]);
  const before = run("standings('D')");
  const rows = run("playInProjection('D')");
  assert.equal(rows[0].nome,R);
  assert.equal(rows[1].admission,'same-club');
  assert.match(run("playInSlot(playInProjection('D')[1])"),/Non ammessa – stessa società/);
  assert.doesNotMatch(run("playInSlot(playInProjection('D')[1])"),/Third/);
  assert.deepEqual(run("standings('D')"),before);
});
test('Bianco can be selected; direct encounter precedes overall quotient', () => {
  const run = setup([R,B,'X','Y'], [game(1,B,R,[50,49]),game(2,R,'X',[100,10]),game(3,B,'Y',[10,100])]);
  assert.equal(run("playInProjection('D').find(t => t.nome === 'POLISPORTIVA REBA').admission"),'same-club');
});
test('direct quotient resolves a split series before overall quotient', () => {
  const run = setup([R,B,'X'], [game(1,R,B,[60,40]),game(2,B,R,[50,40])]);
  assert.equal(run("playInProjection('D')[0].nome"),R);
  assert.equal(run("playInProjection('D')[1].admission"),'same-club');
});
test('residual ties and empty season never select by input order', () => {
  for (const games of [[],[game(1,R,B,[50,40]),game(2,B,R,[50,40])]]) {
    const run=setup([R,B],games);
    assert.deepEqual(run("playInProjection('D').map(t=>t.admission)"),['unresolved','unresolved']);
    assert.match(run("playInSlot(playInProjection('D')[0])"),/da definire/);
  }
});
test('manual simulation and reset recompute selection without changing official scores', () => {
  const run=setup([R,B], [game(1,R,B,null)]);
  run('sim[1] = [40,60]');
  assert.equal(run("playInProjection('D')[0].nome"),B);
  assert.equal(run('db.partite[0].risultato'),null);
  run('sim = {}');
  assert.equal(run("playInProjection('D')[0].admission"),'unresolved');
});
test('full season simulation enforces one REBA candidate and preserves source data', () => {
  const fixture=JSON.parse(fs.readFileSync('data/campionato.json','utf8'));
  const context=vm.createContext({console, Date, Math, document:{querySelector:()=>null}});
  vm.runInContext(source,context);
  context.fixture=fixture;
  vm.runInContext('db=fixture; render=()=>{}',context);
  const before=JSON.stringify(fixture);
  for(let i=0;i<20;i++) {
    vm.runInContext('sim={}; simulateRemaining()',context);
    assert.ok(vm.runInContext("playInProjection('D').filter(t=>REBA_TEAMS.includes(t.nome)&&t.admission==='eligible').length <= 1",context));
    assert.equal(JSON.stringify(fixture),before);
  }
});
