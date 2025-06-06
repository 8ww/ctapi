// ==UserScript==
// @name         答案收录
// @version      1.0.0
// @namespace    xuexim
// @description  答案收录脚本，修复 ed_complete 和题目识别问题，仅在“已完成”状态收录答案
// @author       xuexim
// @match        *://*.chaoxing.com/*
// @connect      127.0.0.1
// @run-at       document-end
// @grant        unsafeWindow
// @grant        GM_xmlhttpRequest
// @license      MIT
// @require      https://cdn.staticfile.org/limonte-sweetalert2/11.0.1/sweetalert2.all.min.js
// @require      https://cdn.staticfile.org/jquery/3.6.0/jquery.min.js
// ==/UserScript==

(function() {
    'use strict';

    var _self = unsafeWindow,
        url = location.pathname,
        top = _self,
        Swal = _self.Swal || window.Swal,
        _host = "http://127.0.0.1:5000";

    // 设置跨域访问的 document.domain
    if (url !== '/studyApp/studying' && top !== _self.top) {
        try {
            document.domain = location.host.replace(/^.+\./, '');
        } catch (e) {
            console.warn("无法设置 document.domain:", e);
        }
    }

    // 查找顶层窗口
    try {
        while (top !== _self.top) {
            top = top.parent.document ? top.parent : _self.top;
            if (top.location.pathname === '/mycourse/studentstudy') break;
        }
    } catch (err) {
        console.warn("查找顶层窗口失败:", err);
        top = _self;
    }

    var $ = _self.jQuery || top.jQuery,
        parent = _self === top ? _self : _self.parent,
        Ext = _self.Ext || parent.Ext || {};

    // 修复 parent.ed_complete
    if (url.endsWith('/work/selectWorkQuestionYiPiYue')) {
        try {
            if (!parent.ed_complete) {
                parent.ed_complete = function() {
                    console.log("模拟调用 ed_complete，任务标记为完成。");
                };
            }
        } catch (e) {
            console.warn("无法定义 parent.ed_complete:", e);
        }
    }

    // 检查完成状态
    function isCompleted() {
        var $status = $('.testTit_status');
        return $status.length && $status.hasClass('testTit_status_complete') && $status.text().includes('已完成');
    }

    // 根据页面类型处理
    if (['/work/doHomeWorkNew', '/mooc-ans/work/doHomeWorkNew', '/api/work', '/work/addStudentWorkNewWeb'].includes(url)) {
        if (isCompleted()) {
            submitAnswer($(document.body), []);
        } else {
            console.log('未检测到“已完成”状态，跳过答案收录。');
        }
    } else if (url.endsWith('/work/selectWorkQuestionYiPiYue')) {
        if (isCompleted()) {
            var data = parent._data ? $.extend(true, [], parent._data) : [];
            submitAnswer(getIframe().parent(), data);
        } else {
            console.log('未检测到“已完成”状态，跳过答案收录。');
        }
    }

    function getIframe(tip, win, job) {
        win = win || _self;
        job = null;
        try {
            while (win && win.frameElement) {
                job = $(win.frameElement).prevAll('.ans-job-icon');
                if (job.length) break;
                win = win.parent;
            }
        } catch (e) {
            console.warn("getIframe 错误:", e);
        }
        return tip ? win : (job || $([]));
    }

    function escapeString(str) {
        if (typeof str !== 'string') return str;
        return str.replace(/\\/g, '\\\\')
            .replace(/'/g, "\\'")
            .replace(/"/g, '\\"');
    }

    function submitAnswer($job, data) {
        if (!$job.length && !$('body').length) {
            console.warn("未找到有效的 job 元素或 body。");
            return;
        }

        $job = $job.length ? $job : $('body');
        $job.removeClass('ans-job-finished');

        // 如果没有提供数据，从 DOM 提取
        if (!data.length) {
            data = $('.TiMu').map(function(index) {
                var $this = $(this),
                    $title = $('.Zy_TItle .clearfix', $this),
                    titleText = filterImg($title).replace(/^【.*?】\s*/, ''),
                    typeText = $title.find('.newZy_TItle').text().match(/【(.*?)】/),
                    typeMap = { "单选题": "1", "多选题": "2", "填空题": "4", "判断题": "3" },
                    type = typeText && typeMap[typeText[1]] !== undefined ? typeMap[typeText[1]] : null;

                if (!type) {
                    console.warn(`题目 ${index + 1} 类型未知:`, typeText ? typeText[1] : '无');
                    return null;
                }

                var optionTexts = $('.Zy_ulTop li', $this).map(function() {
                    return filterImg($(this).find('a')).trim();
                }).get();

                if (!optionTexts.length && type === "3") {
                    optionTexts = ['正确', '错误'];
                }

                var $answerBox = $this.find('.newAnswerBx .myAnswerBx'),
                    answerText = $answerBox.find('.answerCon').text().trim();

                if (!answerText) {
                    console.warn(`题目 ${index + 1} 未找到答案:`, titleText);
                    return null;
                }

                // 检查答案是否正确
                var isCorrect = $answerBox.find('.CorrectOrNot .marking_dui').length > 0;
                if (!isCorrect) {
                    console.log(`题目 ${index + 1} 答案错误，跳过收录:`, titleText);
                    return null;
                }

                var answerOptions = [];
                if (type === "1" || type === "2") {
                    var selectedKeys = answerText.split('').sort();
                    answerOptions = selectedKeys.map(function(key) {
                        var index = key.charCodeAt(0) - 65; // A=0, B=1, etc.
                        var option = optionTexts[index];
                        if (!option) {
                            console.warn(`题目 ${index + 1} 选项 ${key} 无对应文本`);
                        }
                        return option || '';
                    }).filter(Boolean);
                } else if (type === "3") {
                    answerOptions = [answerText === '对' ? '正确' : '错误'];
                } else if (type === "4") {
                    answerOptions = [answerText];
                }

                var option = answerOptions.join('#') || '';
                if (!option) {
                    console.warn(`题目 ${index + 1} 答案无效:`, titleText);
                    return null;
                }

                // 转义 optionTexts
                var escapedOptionTexts = optionTexts.map(function(text) {
                    return escapeString(text);
                });

                console.log(`题目 ${index + 1} 数据:`, {
                    question: titleText,
                    type: type,
                    option: option,
                    optionTexts: escapedOptionTexts,
                    jsonOptionTexts: JSON.stringify(escapedOptionTexts)
                });

                return {
                    question: titleText,
                    option: option,
                    type: type,
                    optionTexts: escapedOptionTexts
                };
            }).get().filter(Boolean);
        } else {
            // 处理 parent._data（不常用，保持原逻辑）
            data = data.map(function(item) {
                if (!item || !item.question || item.type === undefined || !item.option) {
                    return null;
                }
                var typeMap = { 0: "1", 1: "2", 2: "4", 3: "3" };
                var option = Array.isArray(item.option) ? item.option.join('#') : item.option;
                var optionTexts = Array.isArray(item.optionTexts) ? item.optionTexts : (item.optionTexts ? [item.optionTexts] : []);
                var escapedOptionTexts = optionTexts.map(function(text) {
                    return escapeString(text);
                });
                console.log(`parent._data 题目:`, {
                    question: item.question,
                    type: typeMap[item.type] || "4",
                    option: option,
                    optionTexts: escapedOptionTexts,
                    jsonOptionTexts: JSON.stringify(escapedOptionTexts)
                });
                return {
                    question: item.question,
                    option: option,
                    type: typeMap[item.type] || "4",
                    optionTexts: escapedOptionTexts
                };
            }).filter(Boolean);
        }

        // 过滤无效答案
        data = data.filter(function(item) {
            return item && item.option;
        });

        if (!data.length) {
            console.log('没有可提交的答案。');
            Swal && Swal.fire({
                icon: 'info',
                title: '无答案可收录',
                text: '没有找到有效的答案数据，请检查页面内容！',
                timer: 3000,
                showConfirmButton: false
            });
            return;
        }

        // 准备提交数据
        data = data.map(function(item) {
            return {
                question: item.question,
                option: item.option,
                type: item.type,
                optionTexts: JSON.stringify(item.optionTexts)
            };
        });

        // 提交答案
        GM_xmlhttpRequest({
            method: 'POST',
            url: _host + '/cx_update',
            headers: {
                'Content-Type': 'application/json'
            },
            data: JSON.stringify({ data: data }),
            onload: function(response) {
                var res;
                try {
                    res = JSON.parse(response.responseText);
                } catch (e) {
                    res = { code: -1, msg: '无效的响应格式' };
                }

                if (response.status >= 200 && response.status < 300 && res.code === 1) {
                    console.log('答案收录成功:', data);
                    Swal && Swal.fire({
                        icon: 'success',
                        title: '答案收录成功',
                        text: res.msg || '答案已成功提交到服务器！',
                        timer: 3000,
                        showConfirmButton: false
                    });
                    $job.addClass('ans-job-finished');
                } else {
                    console.error('答案收录失败:', res.msg || response.statusText);
                    Swal && Swal.fire({
                        icon: 'error',
                        title: '答案收录失败',
                        text: res.msg || '提交失败，请稍后重试！',
                        timer: 3000,
                        showConfirmButton: false
                    });
                }
            },
            onerror: function(err) {
                console.error('答案收录错误:', err);
                Swal && Swal.fire({
                    icon: 'error',
                    title: '答案收录错误',
                    text: '无法连接到服务器，请确保 http://127.0.0.1:5000 正在运行且无代理干扰！',
                    timer: 5000,
                    showConfirmButton: true
                });
            }
        });
    }

    function filterImg(dom) {
        if (!dom || !dom.length) return '';
        return dom.clone()
            .find('img[src]').replaceWith(function() {
            return $('<p></p>').text('<img src="' + $(this).attr('src') + '">');
        }).end()
            .find('iframe[src]').replaceWith(function() {
            return $('<p></p>').text('<iframe src="' + $(this).attr('src') + '"></iframe>');
        }).end()
            .text().trim();
    }
})();