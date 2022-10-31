# Introduction
Mobility data is the geographic locations of a device, passively produced through normal activity. It has important applications ranging from transportation planning to migration forecasting. As mobility data is rare and hard to collect, researchers have begun exploring solutions for synthetically generating it.

This repo sugest a naive solution for generating synthetic mobility data. This synthetic data can be used for research purposes and for training / fine-tuning algorithms.
The code can be found here and you can use this colab notebook to try it yourself.

Use this [this colab notebook](https://colab.research.google.com/drive/1b7Plly940-GYgjNdP0C-klabDyPiMfUg?usp=sharing) to try it yourself

![Alt Text](https://media.giphy.com/media/74I5JQiRwHMikGT8bO/giphy.gif) 

# Install
-pytohn 3.7+
```
pip install -r requirements.py
```


# Run
```
# examples for params
lat = 30.351043
lng = -97.731965
radius = 2000
n_devices = 2
start_date = '2022-01-01'
end_date = '2022-01-03'
export_path = '/content'
kaggle_username = '<your_kaggle_username_here>'
kaggle_key = '<your_kaggle_key_here>'

from synthetic_mobility_data_generator.main import main as timeline_generator
timeline_generator(lat, lng, radius, n_devices,start_date, end_date,
                   export_path,kaggle_username, kaggle_key, viz_timeline=True)
```
