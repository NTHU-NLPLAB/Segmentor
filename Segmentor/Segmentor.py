#!/usr/bin/python
# coding: utf8
#
#    This file is part of the NAER Segmentor  -
#    Copyright (c) 2016 National Academy for Educational Research
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# ==========================================
# use crf POS tagger
# ==========================================
from __future__ import print_function, unicode_literals
from os import path
import re
import json
import pickle
import time
import subprocess
import CRFPP

# set ../Data directory as default model directory
__default_model_dir__ = path.join(path.abspath(path.dirname(__file__)), 'Data')


class Segmentor(object):
    # 中文字元
    __ch = '[\u4E00-\u9fa5]'

    # 英文字元
    __eng = '[a-zA-Z0-9_ａ-ｚＡ-Ｚ０-９－＿]'

    # 英文字元+符號
    __eng_sym = '[a-zA-Z0-9_ａ-ｚＡ-Ｚ０-９－＿\\/,.&\-]'

    # 其他字元
    __other = '[^\w\u4E00-\u9fa5\s]'

    ##
    _to_tokens_pattern = '{0}|{1}{2}*|{3}'.format(__ch, __eng, __eng_sym, __other)

    def __init__(self, model_dir=__default_model_dir__):
        MIDic = path.join(model_dir, 'DefaultMI.pickle')
        WordDic = path.join(model_dir, 'WordDic.pickle')
        CRFModel = path.join(model_dir, 'DefaultModel')

        # 載入 char bigram MI
        self.MIDic = pickle.load(open(MIDic, 'rb'))

        # 載入簡單字典
        self.WordDic = pickle.load(open(WordDic, 'rb'))

        # 指定 CRF 模型檔名
        self.CRFModel = CRFModel

        # CRF 模組
        self.tagger = CRFPP.Tagger("-m " + self.CRFModel)

        self._to_tokens_rule = re.compile(Segmentor._to_tokens_pattern)

    def __getTokens(self, sent):
        '''divide the data into tokens'''
        tokens = [data for data in self._to_tokens_rule.findall(sent)]
        return tokens

    def __getMIfeature(self, words):
        try:
            return self.MIDic[words]
        except:
            return "MI=X"

    def __generateFeatures(self, tokens_list, stage):
        '''generate features for input data'''

        # 選擇 training 或是 test 的 MI 資料
        token_features = []  # store the (token,features) information

        # token_features 的格式:
        # [
        # 	[ token_1 ,[fea_1, fea_2, ..., fea_n]],
        # 	[ token_2 ,[fea_1, fea_2, ..., fea_n]],
        #  	...
        # ]
        for i in range(len(tokens_list)):
            token_features.append([tokens_list[i], ["NULL" for _ in range(5)]])

        # ======================================
        # 開始加上各種特徵值
        # ======================================
        token_no = len(token_features)

        for i in range(token_no):
            # ===========  Character Type =============
            # 標上字的類別
            # 如果是中文字就直接輸出
            if token_features[i][0] >= '\u4e00' and token_features[i][0] <= '\u9fff':
                token_features[i][1][0] = "CH"
            elif len(token_features[i][0]) == 1 and len(token_features[i][0]) > 1:  # 全形符號
                token_features[i][1][0] = "PUNC"
            elif len(token_features[i][0]) == 1 and token_features[i][0] in ".,!?;'\"/-":
                token_features[i][1][0] = "PUNC"
            else:
                token_features[i][1][0] = "FW"

            # ===========  MI  =============
            # 標上MI的等級
            if i == 0:
                token_features[i][1][1] = self.__getMIfeature(("", token_features[i][0]))
            else:
                token_features[i][1][1] = self.__getMIfeature((token_features[i - 1][0], token_features[i][0]))

            # ===========  二字構詞規則  =============
            # 疊字規則: 2 字, AA
            if i < token_no - 1:
                if token_features[i][1][2] == "NULL":  # 還沒有判斷過 或是有map到之前的規則
                    if token_features[i][0] == token_features[i + 1][0]:  # 符合AA規則
                        token_features[i][1][2] = "P2_1"
                        token_features[i + 1][1][2] = "P2_2"
                    else:  # 沒有符合此規則
                        token_features[i][1][2] = "X"
            else:
                token_features[i][1][2] = "X"

            # ===========  三字構詞規則  =============
            # 疊字規則: 3 字, AAA, ABB, AAB, AXA, A in D and BC in D
            if i < token_no - 2:
                Check_Result = False
                if token_features[i][1][3] == "NULL":  # 還沒有判斷過 或是有map到之前的規則
                    # 三疊字 AAA
                    if token_features[i][0] == token_features[i + 1][0] and  \
                       token_features[i][0] == token_features[i + 2][0]:  # 符合AAA規則
                        Check_Result = True

                    else:  # 也沒有符合AAA規則 檢查ABB
                        if token_features[i][0] != token_features[i + 1][0] and \
                           token_features[i + 1][0] == token_features[i + 2][0]:  # 符合ABB規則

                            Check_Result = True

                        else:  # 也沒有符合ABB規則 檢查AAB
                            if token_features[i][0] == token_features[i + 1][0] and \
                               token_features[i + 1][0] != token_features[i + 2][0]:  # 符合AAB規則

                                Check_Result = True

                            else:  # 也沒有符合AAB規則 檢查AXA
                                if token_features[i][0] == token_features[i + 2][0] and \
                                   token_features[i][0] != token_features[i + 1][0]:  # 符合AXA規則

                                    Check_Result = True

                                else:  # 也沒有符合AXA規則 檢查A-BC
                                    if token_features[i][0] in self.WordDic and \
                                       token_features[i + 1][0] + token_features[i + 2][0] in self.WordDic:  # 符合A-BC規則

                                        Check_Result = True
                    if Check_Result:
                        token_features[i][1][3] = "P3_1"
                        token_features[i + 1][1][3] = "P3_2"
                        token_features[i + 2][1][3] = "P3_3"
                    else:
                        token_features[i][1][3] = "X"
            else:
                token_features[i][1][3] = "X"

            # ===========  四字構詞規則  =============
            # 疊字規則: 4 字, AABB, ABAB, AxAy, xByB
            if i < token_no - 3:
                Check_Result = False
                if token_features[i][1][4] == "NULL":  # 還沒有判斷過 或是有map到之前的規則
                    if token_features[i][0] == token_features[i + 1][0] and \
                       token_features[i + 2][0] == token_features[i + 3][0]:  # 符合AABB規則

                        Check_Result = True

                    else:  # 檢查ABAB
                        if token_features[i][0] == token_features[i + 2][0] and \
                           token_features[i + 1][0] == token_features[i + 3][0]:  # 符合ABAB規則

                            Check_Result = True

                        else:  # 檢查AxAy
                            if token_features[i][0] == token_features[i + 2][0] and \
                               token_features[i + 1][0] != token_features[i + 3][0]:  # 符合AxAy規則

                                Check_Result = True

                            else:  # 檢查xByB
                                if token_features[i][0] != token_features[i + 2][0] and \
                                   token_features[i + 1][0] == token_features[i + 3][0]:  # 符合xByB規則

                                    Check_Result = True

                    if Check_Result:
                        token_features[i][1][4] = "P4_1"
                        token_features[i + 1][1][4] = "P4_2"
                        token_features[i + 2][1][4] = "P4_3"
                        token_features[i + 3][1][4] = "P4_4"
                    else:
                        token_features[i][1][4] = "X"
            else:
                token_features[i][1][4] = "X"

        return token_features

    def generateTrainingData(self, raw_file, training_file):
        """parameters:
                raw_file: the name of the raw file ('e.g., /Data/rawfile')
                training_file: the name of training file used for CRF ('e.g., /Data/trainfile')
        """

        train_file = open(raw_file, 'r')
        out_file = open(training_file, 'w')

        line = train_file.readline()

        while line:

            words = line.strip().split('\t')

            tokenLabel_list = []

            # tokenization stage
            for word in words:

                tokens = self.__getTokens(word)  # divide word into tokens
                try:
                    if len(tokens) == 1:  # "S" for only one token
                        tokenLabel_list.append((tokens[0], "S"))
                    else:
                        tokenLabel_list.append((tokens[0], "B"))
                except:  # for capture errors
                    print("|".join(words))
                    print(word)
                    print(tokens)

                # more than 1 token
                if len(tokens) > 1:
                    for token_i in range(1, len(tokens)):
                        if token_i < len(tokens) - 1:
                            tokenLabel_list.append((tokens[token_i], "I"))
                        else:
                            tokenLabel_list.append((tokens[token_i], "E"))

            # get features of the original data
            TokenFeatures = self.__generateFeatures(
                [data[0] for data in tokenLabel_list], "train")  # (token,[Features])

            # store the training data
            for i in range(len(TokenFeatures)):
                out_str = "%s\t%s\t%s\n" % (TokenFeatures[i][0], "\t".join(
                    TokenFeatures[i][1]), tokenLabel_list[i][1])
                out_file.write(out_str)

            out_file.write('\n')  # add one row for split sentence

            line = train_file.readline()

        train_file.close()
        out_file.close()

        print("training data is generated in %s " % training_file, time.ctime())

        return True

    def train(self, template_file, training_file, model_name):
        '''parameters:
                template_file: the name of template file for CRF learning ('e.g., /model/template_file1')
                training_file: the name of training file ('e.g., /Data/trainfile')
                model_name: the name of the generated model ('e.g., /model/Model_1')
        '''
        print("start training", time.ctime())
        subprocess.check_output(["crf_learn", "-f", "3", template_file, training_file, model_name])
        print("training completed", time.ctime())
        return True

    def procSents(self, sents):
        L = []
        for sent in sents:
            L.append(self.procSent(sent))
        return L

    def _tag_tokens(self, sent):
        # toke			##tokenize the input text
        self.tagger.clear()

        # tokens 的 item 是每一個字
        tokens = self.__getTokens(sent)

        # get features for labeling
        # 每個字都加上一些 features
        token_features = self.__generateFeatures(tokens, 'test')

        # 因為 model 是用 UTF-8 格式建立的，所以執行 CRF tagger 時，要先轉成 UTF-8 字串，再餵入 tagger
        for fea in token_features:
            x = (fea[0] + " " + ' '.join(fea[1]))
            self.tagger.add(x)

        # parse and change internal stated as parsed
        self.tagger.parse()

        seg_result = []

        for i in range(self.tagger.size()):
            seg_result.append([])
            for j in range(self.tagger.xsize()):
                seg_result[-1].append(self.tagger.x(i, j))

            seg_result[-1].append(self.tagger.y2(i))

        # 由於 tagger 的 model 是 UTF-8 建立的，所以輸出也是 UTF-8 碼
        # 執行完成之後，要再轉回 UNICODE
        tagged_tokens = [(data[0], data[-1])
                         for data in seg_result]
        return tagged_tokens

    def _assemble_tokens(self, tagged_tokens):
        # start to assemble the tokens
        words = []
        temp_word = ""
        for now_char, BI in tagged_tokens:
            if BI == "S":
                if len(temp_word) > 0:  # 已經有詞 先輸出
                    words.append(temp_word)
                # 加上本身自己的詞
                words.append(now_char)
                temp_word = ""

            elif BI == "B":
                if len(temp_word) > 0:  # 已經有詞 先輸出
                    words.append(temp_word)

                temp_word = now_char
            elif BI == "I" or BI == "E":

                if re.match('[a-zA-Z0-9_][a-zA-Z0-9_\\/,.&\-]*$', now_char):
                    temp_word += " " + now_char  # (英文及符號之後須考慮多加空白)
                else:
                    temp_word += now_char
        if len(temp_word) > 0:
            words.append(temp_word)  # 最後一個詞

        return words

    def procSent(self, sent):
        tagged_tokens = self._tag_tokens(sent)
        words = self._assemble_tokens(tagged_tokens)

        return words

    segment = procSent


if __name__ == "__main__":
    a = Segmentor()
    doc = (
        "思想引發行動(Sow a thought and you reap an act.)，\n"
        "行動漸成習慣(Sow an act and you reap a habit)，\n"
        "習慣塑造品格(Sow a habit and you reap a character.)，\n"
        "品格決定命運(Sow a character and you reap a destiny.)。\n"
    )
    sents = doc.splitlines()
    print(json.dumps(sents, ensure_ascii=False))

    L = a.procSents(sents)
    print(json.dumps(L, ensure_ascii=False))
