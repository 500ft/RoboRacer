from gym.envs.registration import register

try:
	from gym.wrappers.env_checker import PassiveEnvChecker  # noqa: F401
	_modern_registration = {"disable_env_checker": True, "order_enforce": False}
except ImportError:
	_modern_registration = {}

register(
	id='f110-v0',
	entry_point='f110_gym.envs:F110Env',
	**_modern_registration,
	)
