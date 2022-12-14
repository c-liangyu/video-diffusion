import argparse
import inspect
import random

import numpy as np
import torch

from . import gaussian_diffusion as gd
from .respace import SpacedDiffusion, space_timesteps
from .unet import CondMargVideoModel, SuperResModel, UNetModel, UNetVideoModel

NUM_CLASSES = 1000


def model_and_diffusion_defaults():
    """Defaults for image training."""
    return dict(
        image_size=-1,  # use default image size dict
        num_channels=128,
        num_res_blocks=2,
        num_heads=4,
        num_heads_upsample=-1,
        attention_resolutions='16,8',
        dropout=0.0,
        learn_sigma=False,
        sigma_small=False,
        class_cond=False,
        diffusion_steps=1000,
        noise_schedule='linear',
        timestep_respacing='',
        use_kl=False,
        predict_xstart=False,
        rescale_timesteps=True,
        rescale_learned_sigmas=True,
        use_checkpoint=False,
        use_scale_shift_norm=True,
        use_spatial_encoding=False,
    )


def video_model_and_diffusion_defaults():
    defaults = model_and_diffusion_defaults()
    defaults['T'] = -1
    defaults['use_spatial_encoding'] = True
    defaults['use_frame_encoding'] = False
    defaults['cross_frame_attention'] = True
    defaults['do_cond_marg'] = True
    defaults['enforce_position_invariance'] = False
    defaults['temporal_augment_type'] = 'add_manyhead_presoftmax_time'
    defaults['use_rpe_net'] = True
    defaults[
        'cond_emb_type'] = 'channel'  # channel, channel-initzero, duplicate, duplicate-initzero, or t=0
    defaults['rp_alpha'] = None
    defaults['rp_beta'] = None
    defaults['rp_gamma'] = None
    defaults['allow_interactions_between_padding'] = True
    return defaults


def create_model_and_diffusion(
    image_size,
    class_cond,
    learn_sigma,
    sigma_small,
    num_channels,
    num_res_blocks,
    num_heads,
    num_heads_upsample,
    attention_resolutions,
    dropout,
    diffusion_steps,
    noise_schedule,
    timestep_respacing,
    use_kl,
    predict_xstart,
    rescale_timesteps,
    rescale_learned_sigmas,
    use_checkpoint,
    use_scale_shift_norm,
    use_spatial_encoding,
):
    model = create_model(
        image_size,
        num_channels,
        num_res_blocks,
        learn_sigma=learn_sigma,
        class_cond=class_cond,
        use_checkpoint=use_checkpoint,
        attention_resolutions=attention_resolutions,
        num_heads=num_heads,
        num_heads_upsample=num_heads_upsample,
        use_scale_shift_norm=use_scale_shift_norm,
        dropout=dropout,
        use_spatial_encoding=use_spatial_encoding,
    )
    diffusion = create_gaussian_diffusion(
        steps=diffusion_steps,
        learn_sigma=learn_sigma,
        sigma_small=sigma_small,
        noise_schedule=noise_schedule,
        use_kl=use_kl,
        predict_xstart=predict_xstart,
        rescale_timesteps=rescale_timesteps,
        rescale_learned_sigmas=rescale_learned_sigmas,
        timestep_respacing=timestep_respacing,
    )
    return model, diffusion


def create_video_model_and_diffusion(
    T,
    image_size,
    class_cond,
    learn_sigma,
    sigma_small,
    num_channels,
    num_res_blocks,
    num_heads,
    num_heads_upsample,
    attention_resolutions,
    dropout,
    diffusion_steps,
    noise_schedule,
    timestep_respacing,
    use_kl,
    predict_xstart,
    rescale_timesteps,
    rescale_learned_sigmas,
    use_checkpoint,
    use_scale_shift_norm,
    use_spatial_encoding,
    use_frame_encoding,
    cross_frame_attention,
    do_cond_marg,
    enforce_position_invariance,
    temporal_augment_type,
    use_rpe_net,
    rp_alpha,
    rp_beta,
    rp_gamma,
    cond_emb_type,
    allow_interactions_between_padding,
):
    model = create_video_model(
        T,
        image_size,
        num_channels,
        num_res_blocks,
        learn_sigma=learn_sigma,
        class_cond=class_cond,
        use_checkpoint=use_checkpoint,
        attention_resolutions=attention_resolutions,
        num_heads=num_heads,
        num_heads_upsample=num_heads_upsample,
        use_scale_shift_norm=use_scale_shift_norm,
        dropout=dropout,
        use_spatial_encoding=use_spatial_encoding,
        use_frame_encoding=use_frame_encoding,
        cross_frame_attention=cross_frame_attention,
        do_cond_marg=do_cond_marg,
        enforce_position_invariance=enforce_position_invariance,
        temporal_augment_type=temporal_augment_type,
        use_rpe_net=use_rpe_net,
        rp_alpha=rp_alpha,
        rp_beta=rp_beta,
        rp_gamma=rp_gamma,
        cond_emb_type=cond_emb_type,
        allow_interactions_between_padding=allow_interactions_between_padding,
    )
    diffusion = create_gaussian_diffusion(
        steps=diffusion_steps,
        learn_sigma=learn_sigma,
        sigma_small=sigma_small,
        noise_schedule=noise_schedule,
        use_kl=use_kl,
        predict_xstart=predict_xstart,
        rescale_timesteps=rescale_timesteps,
        rescale_learned_sigmas=rescale_learned_sigmas,
        timestep_respacing=timestep_respacing,
    )
    return model, diffusion


def create_model(
    image_size,
    num_channels,
    num_res_blocks,
    learn_sigma,
    class_cond,
    use_checkpoint,
    attention_resolutions,
    num_heads,
    num_heads_upsample,
    use_scale_shift_norm,
    dropout,
    use_spatial_encoding,
):
    if image_size == 256:
        channel_mult = (1, 1, 2, 2, 4, 4)
    elif image_size == 64:
        channel_mult = (1, 2, 3, 4)
    elif image_size == 32:
        channel_mult = (1, 2, 2, 2)
    else:
        raise ValueError(f'unsupported image size: {image_size}')

    attention_ds = []
    for res in attention_resolutions.split(','):
        attention_ds.append(image_size // int(res))

    return UNetModel(
        in_channels=3,
        model_channels=num_channels,
        out_channels=(3 if not learn_sigma else 6),
        num_res_blocks=num_res_blocks,
        attention_resolutions=tuple(attention_ds),
        dropout=dropout,
        channel_mult=channel_mult,
        num_classes=(NUM_CLASSES if class_cond else None),
        use_checkpoint=use_checkpoint,
        num_heads=num_heads,
        num_heads_upsample=num_heads_upsample,
        use_scale_shift_norm=use_scale_shift_norm,
        use_spatial_encoding=use_spatial_encoding,
        image_size=image_size,
    )


def create_video_model(
    T,
    image_size,
    num_channels,
    num_res_blocks,
    learn_sigma,
    class_cond,
    use_checkpoint,
    attention_resolutions,
    num_heads,
    num_heads_upsample,
    use_scale_shift_norm,
    dropout,
    use_spatial_encoding,
    use_frame_encoding,
    cross_frame_attention,
    do_cond_marg,
    enforce_position_invariance,
    temporal_augment_type,
    use_rpe_net,
    rp_alpha,  # Alpha parameter of RPE attention
    rp_beta,  # Beta parameter of RPE attention
    rp_gamma,  # Gamma parameter of RPE attention
    cond_emb_type,
    allow_interactions_between_padding,
):
    if image_size == 256:
        channel_mult = (1, 1, 2, 2, 4, 4)
    elif image_size == 128:
        channel_mult = (1, 1, 2, 3, 4)
    elif image_size == 64:
        channel_mult = (1, 2, 3, 4)
    elif image_size == 32:
        channel_mult = (1, 2, 2, 2)
    else:
        raise ValueError(f'unsupported image size: {image_size}')

    attention_ds = []
    for res in attention_resolutions.split(','):
        attention_ds.append(image_size // int(res))

    if any([rp_alpha, rp_beta, rp_gamma]):
        bucket_params = dict(alpha=rp_alpha, beta=rp_beta, gamma=rp_gamma)
    else:
        bucket_params = None

    ModelClass = CondMargVideoModel if do_cond_marg else UNetVideoModel
    return ModelClass(
        T=T,
        in_channels=3,
        model_channels=num_channels,
        out_channels=(3 if not learn_sigma else 6),
        num_res_blocks=num_res_blocks,
        attention_resolutions=tuple(attention_ds),
        dropout=dropout,
        channel_mult=channel_mult,
        num_classes=(NUM_CLASSES if class_cond else None),
        use_checkpoint=use_checkpoint,
        num_heads=num_heads,
        num_heads_upsample=num_heads_upsample,
        use_scale_shift_norm=use_scale_shift_norm,
        use_spatial_encoding=use_spatial_encoding,
        use_frame_encoding=use_frame_encoding,
        cross_frame_attention=cross_frame_attention,
        enforce_position_invariance=enforce_position_invariance,
        image_size=image_size,
        temporal_augment_type=temporal_augment_type,
        use_rpe_net=use_rpe_net,
        bucket_params=bucket_params,
        cond_emb_type=cond_emb_type,
        allow_interactions_between_padding=allow_interactions_between_padding,
    )


def sr_model_and_diffusion_defaults():
    res = model_and_diffusion_defaults()
    res['large_size'] = 256
    res['small_size'] = 64
    arg_names = inspect.getfullargspec(sr_create_model_and_diffusion)[0]
    for k in res.copy().keys():
        if k not in arg_names:
            del res[k]
    return res


def sr_create_model_and_diffusion(
    large_size,
    small_size,
    class_cond,
    learn_sigma,
    num_channels,
    num_res_blocks,
    num_heads,
    num_heads_upsample,
    attention_resolutions,
    dropout,
    diffusion_steps,
    noise_schedule,
    timestep_respacing,
    use_kl,
    predict_xstart,
    rescale_timesteps,
    rescale_learned_sigmas,
    use_checkpoint,
    use_scale_shift_norm,
):
    model = sr_create_model(
        large_size,
        small_size,
        num_channels,
        num_res_blocks,
        learn_sigma=learn_sigma,
        class_cond=class_cond,
        use_checkpoint=use_checkpoint,
        attention_resolutions=attention_resolutions,
        num_heads=num_heads,
        num_heads_upsample=num_heads_upsample,
        use_scale_shift_norm=use_scale_shift_norm,
        dropout=dropout,
    )
    diffusion = create_gaussian_diffusion(
        steps=diffusion_steps,
        learn_sigma=learn_sigma,
        noise_schedule=noise_schedule,
        use_kl=use_kl,
        predict_xstart=predict_xstart,
        rescale_timesteps=rescale_timesteps,
        rescale_learned_sigmas=rescale_learned_sigmas,
        timestep_respacing=timestep_respacing,
    )
    return model, diffusion


def sr_create_model(
    large_size,
    small_size,
    num_channels,
    num_res_blocks,
    learn_sigma,
    class_cond,
    use_checkpoint,
    attention_resolutions,
    num_heads,
    num_heads_upsample,
    use_scale_shift_norm,
    dropout,
):
    _ = small_size  # hack to prevent unused variable

    if large_size == 256:
        channel_mult = (1, 1, 2, 2, 4, 4)
    elif large_size == 64:
        channel_mult = (1, 2, 3, 4)
    else:
        raise ValueError(f'unsupported large size: {large_size}')

    attention_ds = []
    for res in attention_resolutions.split(','):
        attention_ds.append(large_size // int(res))

    return SuperResModel(
        in_channels=3,
        model_channels=num_channels,
        out_channels=(3 if not learn_sigma else 6),
        num_res_blocks=num_res_blocks,
        attention_resolutions=tuple(attention_ds),
        dropout=dropout,
        channel_mult=channel_mult,
        num_classes=(NUM_CLASSES if class_cond else None),
        use_checkpoint=use_checkpoint,
        num_heads=num_heads,
        num_heads_upsample=num_heads_upsample,
        use_scale_shift_norm=use_scale_shift_norm,
    )


def create_gaussian_diffusion(
    *,
    steps=1000,
    learn_sigma=False,
    sigma_small=False,
    noise_schedule='linear',
    use_kl=False,
    predict_xstart=False,
    rescale_timesteps=False,
    rescale_learned_sigmas=False,
    timestep_respacing='',
):
    betas = gd.get_named_beta_schedule(noise_schedule, steps)
    if use_kl:
        loss_type = gd.LossType.RESCALED_KL
    elif rescale_learned_sigmas:
        loss_type = gd.LossType.RESCALED_MSE
    else:
        loss_type = gd.LossType.MSE
    if not timestep_respacing:
        timestep_respacing = [steps]
    return SpacedDiffusion(
        use_timesteps=space_timesteps(steps, timestep_respacing),
        betas=betas,
        model_mean_type=(gd.ModelMeanType.EPSILON
                         if not predict_xstart else gd.ModelMeanType.START_X),
        model_var_type=((gd.ModelVarType.FIXED_LARGE
                         if not sigma_small else gd.ModelVarType.FIXED_SMALL)
                        if not learn_sigma else gd.ModelVarType.LEARNED_RANGE),
        loss_type=loss_type,
        rescale_timesteps=rescale_timesteps,
    )


def add_dict_to_argparser(parser, default_dict):
    for k, v in default_dict.items():
        v_type = type(v)
        if v is None:
            v_type = str
        elif isinstance(v, bool):
            v_type = str2bool
        parser.add_argument(f'--{k}', default=v, type=v_type)


def args_to_dict(args, keys):
    backups = {'allow_interactions_between_padding': True}
    return {
        k: getattr(args, k) if hasattr(args, k) else backups[k]
        for k in keys
    }


def str2bool(v):
    """https://stackoverflow.com/questions/15008758/parsing-boolean-values-
    with-argparse."""
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('boolean value expected')


def set_random_seed(seed, deterministic=False):
    """Set random seed.

    Args:
        seed (int): Seed to be used.
        deterministic (bool): Whether to set the deterministic option for
            CUDNN backend, i.e., set `torch.backends.cudnn.deterministic`
            to True and `torch.backends.cudnn.benchmark` to False.
            Default: False.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if deterministic:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
