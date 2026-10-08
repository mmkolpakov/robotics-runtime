import assert from 'node:assert/strict';
/** Validate the existing fixture container before using its current published endpoint. */
export function ownedLoopbackEndpoint(detail,expected){
 assert.match(expected.id,/^[0-9a-f]{64}$/);assert.equal(detail.Id,expected.id);
 assert.equal(detail.Config.Labels['org.robotics.runtime.fixture-owner'],expected.owner);
 assert.equal(detail.Config.Labels['org.robotics.runtime.fixture-suite'],expected.suite);
 assert.deepEqual(Object.keys(detail.NetworkSettings.Networks).sort(),expected.networks.map(n=>n.name).sort());
 for(const network of expected.networks)assert.equal(detail.NetworkSettings.Networks[network.name].NetworkID,network.id);
 assert.equal(detail.State.Running,true);
 const bindings=detail.NetworkSettings.Ports['3000/tcp'];
 assert.equal(bindings.length,1);assert.equal(bindings[0].HostIp,'127.0.0.1');
 assert.match(bindings[0].HostPort,/^[1-9][0-9]{0,4}$/);
 const port=Number(bindings[0].HostPort);assert.ok(port<=65535);
 return {id:detail.Id,url:'http://127.0.0.1:'+port,bindings:[{HostIp:'127.0.0.1',HostPort:String(port)}],
  state:{status:detail.State.Status,running:detail.State.Running,exitCode:detail.State.ExitCode,
   oomKilled:detail.State.OOMKilled,startedAt:detail.State.StartedAt,finishedAt:detail.State.FinishedAt}};
}
