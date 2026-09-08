# Flight controller interface profile

`qualification-profile.json` defines the six required capabilities for a
simulation flight controller. The existing `provider_kind` and provider identity
fields are extensible identifiers, so `flight_controller` needs no schema enum
change. Validate the profile with `robotics-contracts validate` and bind its exact
file digest in both the runtime provider binding and `conformance-result.v1`.

A conformance probe must verify arm/disarm and flight-mode services, local
position, attitude and battery topics, and a clock that follows the simulator.
For the selected implementation, check actual interface names and types, QoS,
observed publication rates and simulation-clock behavior. Report the resulting
checks and retain their evidence. A required capability needs a passing check;
a missing or non-passing capability cannot qualify the provider.

The profile describes interface requirements. ArduPilot AP_DDS, PX4 uXRCE-DDS
and MSP bridges are composition choices made by infrastructure and the product.
Their implementation versions, configuration bytes and observed target identities
belong in the provider binding and conformance result. Interface names, rates and
QoS must come from that implementation's checked configuration; the profile does
not prescribe one controller's ROS namespace.

This example is a requirement set, not a measured conformance result. Live
conformance and mission tests are performed by the infrastructure/product stages.
