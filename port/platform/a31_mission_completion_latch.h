#pragma once

/*
** Dependency-free state latch for the original CombatMiscHandler callbacks.
** The Vita boundary observes terminal mission events; it never creates them
** and never mutates objective, script, campaign, or player state.
*/
struct A31MissionCompletionState
{
	bool completion_observed;
	bool mission_succeeded;
	bool star_killed_observed;
};

class A31MissionCompletionLatch
{
public:
	A31MissionCompletionLatch()
	{
		Reset();
	}

	void Reset()
	{
		StateValue.completion_observed = false;
		StateValue.mission_succeeded = false;
		StateValue.star_killed_observed = false;
	}

	void Mission_Complete(bool success)
	{
		/* Preserve the first original terminal result if a script reports it
		** more than once during the same simulation frame. */
		if (!StateValue.completion_observed) {
			StateValue.completion_observed = true;
			StateValue.mission_succeeded = success;
		}
	}

	void Star_Killed()
	{
		StateValue.star_killed_observed = true;
	}

	A31MissionCompletionState State() const
	{
		return StateValue;
	}

private:
	A31MissionCompletionState StateValue;
};
