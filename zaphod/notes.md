Not sure about the difference between simulation and model right now, but we can talk about the difference between particle and individual.

In CoarseGraining we see three interesting variations of a simulation. The simulation uses particles. Particles are interestingly distinct from individuals.

a. Particles
Process of step i uses object's data from step i-1.
Can substitute any particle for any other particle.
No Names

b. Individuals
Process of step i uses object's data from step i-1.
Must track data from step to step.
Cannot substitute any particle for any other particle. (*why??* Must have at least one property not set by the simulation. Testable!)
Names are convenient

Note that there could be simulations, simple ones, even, in which the individuality of objects might change over time or even under specific conditions of simulation. One example would be a simulation in which the individuality of each object is reduced from step to step, eventually arriving at an identity state where that object is indistinguishable from others that are similarly reduced. In the circle-step simulation we might give every particle a bias in one direction or the other, making them individuals, but then reduce that bias to zero in ten steps. And then we would be seeing a particle simulation, or perhaps we would end the simulation.


### Relationship to scientific computing (CAS 502)

Gathering data about particles is different from gathering data about individuals. 
Particles: speed of processing, elegant algorithms
Individuals: traceability, FAIR stuff



### There is a network

There are obviously networks in CoarseGraining. 

### Note on time

"Steps" "Iterations" "T": Oh, "steps" is fine. "Do the thing `numsteps` times." A step is about the verb. Not about time---but it reminds us of time, because this is how discrete time and causality works. It's sort of important, though, that it *isn't* necessarily time. It's steps.