import numpy as np
import pandas as pd
import traval


def get_model_sim_pi(ml, raw, ci=0.99, tmin=None, tmax=None, smoothfreq=None):
    if ml is not None:
        alpha = 1 - float(ci)

        # get prediction interval
        df_pi = ml.fit.prediction_interval(alpha=alpha)

        if not df_pi.empty:
            if smoothfreq is not None:
                df_pi.iloc[:, 0] = traval.ts_utils.smooth_lower_bound(
                    df_pi.iloc[:, 0], smoothfreq=smoothfreq
                )
                df_pi.iloc[:, 1] = traval.ts_utils.smooth_upper_bound(
                    df_pi.iloc[:, 1], smoothfreq=smoothfreq
                )

            if tmin is not None:
                df_pi = df_pi.loc[tmin:]
            if tmax is not None:
                df_pi = df_pi.loc[:tmax]

            sim = ml.simulate(tmin=tmin, tmax=tmax)

            # interpolate to observations index
            new_idx = raw.index.union(sim.index)
            pi = pd.DataFrame(index=new_idx, columns=df_pi.columns)
            for i in range(2):
                pi.iloc[:, i] = traval.ts_utils.interpolate_series_to_new_index(
                    df_pi.iloc[:, i], new_idx
                )

            sim_interp = traval.ts_utils.interpolate_series_to_new_index(sim, new_idx)
            sim_i = pd.Series(index=new_idx, data=sim_interp)
            sim_i.name = "sim"
        else:
            sim_i = pd.Series(index=raw.index, data=np.nan)
            sim_i.name = "sim"

            pi = pd.DataFrame(index=raw.index, columns=["lower", "upper"], data=np.nan)
    else:
        sim_i = pd.Series(index=raw.index, data=np.nan)
        sim_i.name = "sim"

        pi = pd.DataFrame(index=raw.index, columns=["lower", "upper"], data=np.nan)
    return sim_i, pi.astype(float)
