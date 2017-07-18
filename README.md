# 國教院中文分詞系統 Python 3

## 安裝
* 下載程式碼：

	```$ git clone https://github.com/NTHU-NLPLAB/Segmentor```
    
* 下載分詞及詞性標記模型：
	* 下載處：
		* [naer-segmentor-models-20160318.tar.gz](http://120.127.233.228/download/Segmentor/naer-segmentor-models-20160318.tar.gz)
	* 模型下載後於 Segmentor/Segmentor 目錄下解壓縮

		```
		$ wget http://120.127.233.228/download/Segmentor/naer-segmentor-models-xxx.tar.gz
		$ tar zxvf naer-segmentor-models-xxx.tar.gz -C Segmentor/Segmentor
		```

* 安裝 CRF++
	* 下載處：
		* https://taku910.github.io/crfpp/
	* 安裝 CRF++：

		```
		$ tar zxvf CRF++-058.tar.gz
		$ cd CRF++-058
		$ ./configure
		$ make
		$ sudo make install
		```

	* 安裝 python 介面(CRFPP)：

		
		```
		$ cd python
		$ sudo python setup.py install
		```

*  安裝程式與資料：
	* 在 Segmentor 目錄下執行安裝：

	    ```
	    $ sudo python setup.py install
	    ```

## Segmentor 模組簡易使用方法

```python
import json
from Segmentor import Segmentor
segmenter = Segmentor()
words = segmenter.segment("中文分詞系統。")
print(words)
>> ["中文", "分詞", "系統", "。"]
```
